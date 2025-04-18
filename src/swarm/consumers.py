import json
import os
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from openai import AsyncOpenAI
from django.template.loader import render_to_string
from channels.db import database_sync_to_async
from swarm.models import ChatConversation, ChatMessage

# In-memory conversation storage (populated lazily)
IN_MEMORY_CONVERSATIONS = {}

class DjangoChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']

        if self.user.is_authenticated:
            self.messages = await self.fetch_conversation(self.conversation_id)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.save_conversation(self.conversation_id, self.messages)

            # Delete conversation from DB and memory if empty
            if not self.messages:
                await self.delete_conversation(self.conversation_id)

            # Clean up in-memory cache to avoid leaks
            if self.conversation_id in IN_MEMORY_CONVERSATIONS:
                del IN_MEMORY_CONVERSATIONS[self.conversation_id]

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_text = text_data_json["message"]

        if not message_text.strip():
            return

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

        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # --- PATCH: Enforce LiteLLM-only endpoint and suppress OpenAI tracing/telemetry ---
        import os, logging
        if os.environ.get("LITELLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL"):
            logging.getLogger("openai.agents").setLevel(logging.CRITICAL)
            try:
                import openai.agents.tracing
                openai.agents.tracing.TracingClient = lambda *a, **kw: None
            except Exception:
                pass
        def _enforce_litellm_only(client):
            base_url = getattr(client, 'base_url', None)
            if base_url and 'openai.com' in base_url:
                return
            if base_url and 'openai.com' not in base_url:
                import traceback
                raise RuntimeError(f"Attempted fallback to OpenAI API when custom base_url is set! base_url={base_url}\n{traceback.format_stack()}")
        _enforce_litellm_only(client)
        
        stream = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL"),
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
        if conversation_id in IN_MEMORY_CONVERSATIONS:
            return IN_MEMORY_CONVERSATIONS[conversation_id]

        try:
            chat = ChatConversation.objects.get(conversation_id=conversation_id, user=self.user)
            messages = list(chat.messages.values("sender", "content", "timestamp"))
            IN_MEMORY_CONVERSATIONS[conversation_id] = messages  # Cache it
            return messages
        except ChatConversation.DoesNotExist:
            return []

    @database_sync_to_async
    def save_conversation(self, conversation_id, new_messages):
        """
        Save messages to the DB and update in-memory cache.
        """
        chat, _ = ChatConversation.objects.get_or_create(conversation_id=conversation_id, user=self.user)

        for message in new_messages:
            ChatMessage.objects.create(
                conversation=chat,
                sender=message["role"],
                content=message["content"]
            )

        # Sync in-memory store
        IN_MEMORY_CONVERSATIONS[conversation_id] = new_messages

    @database_sync_to_async
    def delete_conversation(self, conversation_id):
        """
        Delete the conversation from DB if empty.
        """
        try:
            chat = ChatConversation.objects.get(conversation_id=conversation_id, user=self.user)
            if not chat.messages.exists():  # Check if there are any messages before deleting
                chat.delete()
                if conversation_id in IN_MEMORY_CONVERSATIONS:
                    del IN_MEMORY_CONVERSATIONS[conversation_id]  # Cleanup memory cache
        except ChatConversation.DoesNotExist:
            pass
