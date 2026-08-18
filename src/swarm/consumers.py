import json
import logging
import os
import uuid
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.template.loader import render_to_string

from swarm.models import ChatConversation, ChatMessage

logger = logging.getLogger(__name__)

# Lazy sentinel — replaced on first use so the module-level name is patchable in tests.
AsyncOpenAI = None

# In-memory conversation storage (populated lazily).
# Keys are (user_id, conversation_id) to prevent cross-user cache IDOR.
IN_MEMORY_CONVERSATIONS = {}

# Custom close code for anonymous connects (HTTP 401 analogue). Accept-then-close
# so browsers receive a CloseEvent with this code instead of opaque 1006.
WS_AUTH_REQUIRED_CODE = 4401


def _conversation_cache_key(user, conversation_id):
    """Composite cache key so one user's transcript never leaks to another."""
    user_id = getattr(user, "pk", None)
    if user_id is None:
        user_id = getattr(user, "id", None)
    return (user_id, conversation_id)


class DjangoChatConsumer(AsyncWebsocketConsumer):
    """Websocket chat consumer.

    Client -> server frames are JSON: ``{"message": "<text>"}`` with an
    optional ``"blueprint": "<id>"`` field selecting which discovered
    blueprint generates the reply. A connection-level default can also be
    set via the ws URL query string (``?blueprint=<id>``); a per-message
    ``blueprint`` field overrides it. When neither is given, the legacy
    behaviour (server-configured OpenAI model) is preserved.

    Auth is Django **session** only (``AuthMiddlewareStack`` cookie). A
    Settings-page API bearer token does not authenticate this socket.
    """

    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        # Optional connection-level default blueprint (?blueprint=<id>).
        query_params = parse_qs(self.scope.get("query_string", b"").decode())
        self.default_blueprint = (query_params.get("blueprint") or [None])[0]

        if self.user.is_authenticated:
            self.messages = await self.fetch_conversation(self.conversation_id)
            await self.accept()
        else:
            # Accept first so the client sees close code 4401 (not 1006).
            await self.accept()
            await self.close(
                code=WS_AUTH_REQUIRED_CODE,
                reason="authentication required",
            )

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.save_conversation(self.conversation_id, self.messages)

            # Delete conversation from DB and memory if empty
            if not self.messages:
                await self.delete_conversation(self.conversation_id)

            # Clean up in-memory cache to avoid leaks
            cache_key = _conversation_cache_key(self.user, self.conversation_id)
            if cache_key in IN_MEMORY_CONVERSATIONS:
                del IN_MEMORY_CONVERSATIONS[cache_key]

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_text = text_data_json["message"]

        if not message_text.strip():
            return

        # Per-message blueprint selection wins over the connection default.
        blueprint_id = text_data_json.get("blueprint") or getattr(
            self, "default_blueprint", None
        )

        self.messages.append(
            {
                "role": "user",
                "content": message_text,
            }
        )

        user_message_html = render_to_string(
            "websocket_partials/user_message.html",
            {"message_text": message_text},
        )
        await self.send(text_data=user_message_html)

        message_id = uuid.uuid4().hex
        contents_div_id = f"message-response-{message_id}"
        system_message_html = render_to_string(
            "websocket_partials/system_message.html",
            {"contents_div_id": contents_div_id},
        )
        await self.send(text_data=system_message_html)

        if blueprint_id:
            await self.respond_with_blueprint(blueprint_id, contents_div_id)
        else:
            await self.respond_with_default_model(contents_div_id)

    async def respond_with_blueprint(self, blueprint_id, contents_div_id):
        """Generate the assistant reply by running a discovered blueprint."""
        # In test mode, skip slow blueprint instantiation and return canned output.
        if os.environ.get("SWARM_TEST_MODE"):
            from pathlib import Path as _Path
            from django.conf import settings as _settings
            bp_dir = _Path(getattr(_settings, "BLUEPRINT_DIRECTORY", "src/swarm/blueprints"))
            known = {d.name for d in bp_dir.iterdir() if d.is_dir() and not d.name.startswith("_")} if bp_dir.is_dir() else set()
            if blueprint_id not in known:
                await self.send_error_message(
                    contents_div_id,
                    f"Error: blueprint '{blueprint_id}' not found.",
                )
                return
            instruction = self.messages[-1]["content"] if self.messages else ""
            canned = f"[TEST-MODE] Jeeves at your service. You said: '{instruction}'" if blueprint_id == "jeeves" else f"[TEST-MODE] {blueprint_id} at your service. You said: '{instruction}'"
            chunk_html = f'<div hx-swap-oob="beforeend:#{contents_div_id}">{canned}</div>'
            await self.send(text_data=chunk_html)
            self.messages.append({"role": "assistant", "content": canned})
            final_html = render_to_string(
                "websocket_partials/final_system_message.html",
                {"contents_div_id": contents_div_id, "message": canned},
            )
            await self.send(text_data=final_html)
            return

        from swarm.views.chat_views import (
            _chunk_is_final,
            _extract_message_from_chunk,
        )

        try:
            from swarm.views.utils import get_blueprint_instance
            blueprint_instance = await get_blueprint_instance(blueprint_id)
        except Exception:
            logger.error(
                f"Error loading blueprint '{blueprint_id}'", exc_info=True
            )
            blueprint_instance = None

        if blueprint_instance is None:
            await self.send_error_message(
                contents_div_id,
                f"Error: blueprint '{blueprint_id}' was not found or could not be initialized.",
            )
            return

        final_message = None
        try:
            async for chunk in blueprint_instance.run(self.messages):
                message = _extract_message_from_chunk(chunk)
                if message is None:
                    continue
                final_message = message
                if _chunk_is_final(chunk):
                    break
        except Exception as e:
            logger.error(
                f"Error running blueprint '{blueprint_id}': {e}", exc_info=True
            )
            await self.send_error_message(
                contents_div_id,
                f"Error: blueprint '{blueprint_id}' failed while generating a reply.",
            )
            return

        if not isinstance(final_message, dict) or final_message.get("content") is None:
            await self.send_error_message(
                contents_div_id,
                f"Error: blueprint '{blueprint_id}' did not return a reply.",
            )
            return

        full_message = final_message["content"]
        chunk_html = f'<div hx-swap-oob="beforeend:#{contents_div_id}">{full_message}</div>'
        await self.send(text_data=chunk_html)

        self.messages.append(
            {
                "role": "assistant",
                "content": full_message,
            }
        )

        final_message_html = render_to_string(
            "websocket_partials/final_system_message.html",
            {
                "contents_div_id": contents_div_id,
                "message": full_message,
            },
        )
        await self.send(text_data=final_message_html)

    async def send_error_message(self, contents_div_id, error_text):
        """Replace the streaming placeholder with an error partial.

        Transport-level errors (unknown blueprint, execution failure) are
        shown to the user but deliberately NOT appended to ``self.messages``
        so they never pollute the model context of later turns.
        """
        error_html = render_to_string(
            "websocket_partials/final_system_message.html",
            {
                "contents_div_id": contents_div_id,
                "message": error_text,
            },
        )
        await self.send(text_data=error_html)

    async def respond_with_default_model(self, contents_div_id):
        """Legacy reply path: server-configured model via LiteLLM/OpenAI env."""
        import swarm.consumers as _self_mod
        _cls = _self_mod.AsyncOpenAI
        if _cls is None:
            from openai import AsyncOpenAI as _cls
            _self_mod.AsyncOpenAI = _cls

        # Mirror blueprint_base.configure_openai_client_from_env / LITELLM_* patterns.
        base_url = os.environ.get("LITELLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
        api_key = os.environ.get("LITELLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        model = (
            os.environ.get("LITELLM_MODEL")
            or os.environ.get("OPENAI_MODEL")
            or os.environ.get("DEFAULT_LLM")
        )
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = _cls(**client_kwargs)

        if base_url:
            logging.getLogger("openai.agents").setLevel(logging.CRITICAL)
            try:
                import openai.agents.tracing
                openai.agents.tracing.TracingClient = lambda *a, **kw: None
            except Exception:
                pass

        def _enforce_litellm_only(client):
            """Reject openai.com fallback when a custom LiteLLM gateway is configured."""
            expected = os.environ.get("LITELLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
            if not expected:
                return
            actual = str(getattr(client, "base_url", "") or "")
            if not actual or "openai.com" in actual:
                import traceback
                raise RuntimeError(
                    "Attempted fallback to OpenAI API when custom base_url is set! "
                    f"base_url={actual!r} expected={expected!r}\n{traceback.format_stack()}"
                )

        _enforce_litellm_only(client)

        stream = await client.chat.completions.create(
            model=model,
            messages=self.messages,
            stream=True,
        )

        full_message = ""
        async for chunk in stream:
            message_chunk = chunk.choices[0].delta.content
            if message_chunk:
                full_message += message_chunk
                chunk_html = f'<div hx-swap-oob="beforeend:#{contents_div_id}">{message_chunk}</div>'
                await self.send(text_data=chunk_html)

        self.messages.append(
            {
                "role": "assistant",
                "content": full_message,
            }
        )

        final_message = render_to_string(
            "websocket_partials/final_system_message.html",
            {
                "contents_div_id": contents_div_id,
                "message": full_message,
            },
        )
        await client.close()
        await self.send(text_data=final_message)

    @database_sync_to_async
    def fetch_conversation(self, conversation_id):
        """
        Fetch conversation messages from memory or DB. If missing from memory, load from DB.
        """
        cache_key = _conversation_cache_key(self.user, conversation_id)
        if cache_key in IN_MEMORY_CONVERSATIONS:
            return IN_MEMORY_CONVERSATIONS[cache_key]

        try:
            chat = ChatConversation.objects.get(conversation_id=conversation_id, student=self.user)
            messages = [{'role': m['sender'], 'content': m['content']} for m in chat.messages.values("sender", "content")]
            IN_MEMORY_CONVERSATIONS[cache_key] = messages  # Cache it
            return messages
        except ChatConversation.DoesNotExist:
            logger.debug(f"Conversation {conversation_id} not found in database for user: {self.user}")
            return []

    @database_sync_to_async
    def save_conversation(self, conversation_id, new_messages):
        """Replace DB messages with the current in-memory transcript.

        Disconnect always persists the full transcript. Without clearing
        prior rows, reconnect → disconnect would bulk_create duplicates.

        Lookup is by conversation_id PK only (avoids IntegrityError when the
        row exists for another student); ownership is then validated.
        """
        cache_key = _conversation_cache_key(self.user, conversation_id)
        chat, created = ChatConversation.objects.get_or_create(
            conversation_id=conversation_id,
            defaults={"student": self.user},
        )
        if not created and chat.student_id is not None and chat.student_id != self.user.pk:
            logger.warning(
                "Refusing to save conversation %s: owned by another user (requested by %s)",
                conversation_id,
                self.user,
            )
            return
        if chat.student_id is None:
            chat.student = self.user
            chat.save(update_fields=["student"])

        chat_messages = [
            ChatMessage(
                conversation=chat,
                sender=message["role"],
                content=message["content"],
            )
            for message in new_messages
        ]
        # Idempotent replace: delete then insert current transcript.
        ChatMessage.objects.filter(conversation=chat).delete()
        ChatMessage.objects.bulk_create(chat_messages)

        IN_MEMORY_CONVERSATIONS[cache_key] = list(new_messages)

    @database_sync_to_async
    def delete_conversation(self, conversation_id):
        """
        Delete the conversation from DB if empty.
        """
        cache_key = _conversation_cache_key(self.user, conversation_id)
        try:
            chat = ChatConversation.objects.get(conversation_id=conversation_id, student=self.user)
            if not chat.messages.exists():  # Check if there are any messages before deleting
                chat.delete()
                if cache_key in IN_MEMORY_CONVERSATIONS:
                    del IN_MEMORY_CONVERSATIONS[cache_key]  # Cleanup memory cache
        except ChatConversation.DoesNotExist:
            logger.warning(f"Attempted to delete non-existent conversation: {conversation_id} for user: {self.user}")
