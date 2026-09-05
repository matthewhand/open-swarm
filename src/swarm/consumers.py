import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.template.loader import render_to_string
from django.utils.html import escape

from swarm.models import ChatConversation, ChatMessage
from swarm.middleware import (
    client_ip_from_scope,
    get_or_create_preview_user,
    swarm_allow_anonymous,
)

logger = logging.getLogger(__name__)

# Lazy sentinel — replaced on first use so the module-level name is patchable in tests.
AsyncOpenAI = None

# In-memory conversation storage (populated lazily).
# Keys are (user_id, conversation_id) to prevent cross-user cache IDOR.
IN_MEMORY_CONVERSATIONS = {}

# Custom close code for anonymous connects (HTTP 401 analogue). Accept-then-close
# so browsers receive a CloseEvent with this code instead of opaque 1006.
WS_AUTH_REQUIRED_CODE = 4401

# REQ-78 / #423 — advertise the backend's expected SPA bake on connect.
SPA_HELLO_TYPE = "spa_hello"


def _message_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save_agent_json(user, agent_id, messages, *, conversation_id=""):
    """Best-effort write of the per-agent JSON thread (Settings + reload)."""
    if not getattr(user, "is_authenticated", False) or not messages:
        return
    try:
        from swarm.core import chat_store
        from swarm.core.agent_settings import is_new_chat_per_task

        session_id = ""
        if agent_id and is_new_chat_per_task(agent_id) and conversation_id:
            session_id = conversation_id
        chat_store.save(
            chat_store.user_key_for(user),
            agent_id,
            messages,
            conversation_id=conversation_id,
            session_id=session_id,
        )
    except Exception:
        logger.exception("Failed to persist agent chat JSON")


def _load_agent_json(user, agent_id, *, conversation_id=""):
    """Best-effort load of the per-agent JSON thread."""
    if not getattr(user, "is_authenticated", False):
        return []
    try:
        from swarm.core import chat_store
        from swarm.core.agent_settings import is_new_chat_per_task

        session_id = ""
        if agent_id and is_new_chat_per_task(agent_id) and conversation_id:
            session_id = conversation_id
        record = chat_store.load(
            chat_store.user_key_for(user),
            agent_id,
            conversation_id=conversation_id,
            session_id=session_id,
        )
    except Exception:
        logger.exception("Failed to load agent chat JSON")
        return []
    if not record:
        return []
    return [
        {"role": m.get("role", "user"), "content": m.get("content", "")}
        for m in record.get("messages") or []
    ]


def _conversation_cache_key(user, conversation_id):
    """Composite cache key so one user's transcript never leaks to another."""
    user_id = getattr(user, "pk", None)
    if user_id is None:
        user_id = getattr(user, "id", None)
    return (user_id, conversation_id)


async def _compacted_context(conversation_id, messages):
    """Model context: summary tree replaces covered raw turns (REQ-37).

    Raw ``messages`` stay on the consumer and on disk. Failures fall back
    to the filtered list (status/info never reach the model — REQ-70).
    """
    try:
        from swarm.core.chat_compact import context_for_conversation

        return await database_sync_to_async(context_for_conversation)(
            conversation_id, messages
        )
    except Exception:
        logger.debug("compact context unavailable; using filtered transcript", exc_info=True)
        from swarm.core.speaker_identity import apply_speaker_identity
        from swarm.core.transcript_roles import messages_for_model

        return apply_speaker_identity(messages_for_model(messages), adapter_id="openai_compat")


def _status_line_html(text: str) -> str:
    """Bubble-less transcript line (CLI session notice; related to #362)."""
    return (
        '<div id="message-list" hx-swap-oob="beforeend">'
        f'<div class="chat-status-line os-chat-status">{escape(text)}</div>'
        "</div>"
    )


def _oob_append_html(contents_div_id: str, text: str) -> str:
    """HTMX OOB append chunk with HTML-escaped body text.

    Streaming replies previously interpolated model/user text into raw HTML,
    so a payload like ``<img onerror=…>`` executed before the final escaped
    template swap replaced the node.
    """
    return (
        f'<div hx-swap-oob="beforeend:#{contents_div_id}">'
        f"{escape(text)}</div>"
    )


class DjangoChatConsumer(AsyncWebsocketConsumer):
    """Websocket chat consumer.

    Client -> server frames are JSON: ``{"message": "<text>"}`` with an
    optional ``"blueprint": "<id>"`` field selecting which discovered
    blueprint generates the reply. A connection-level default can also be
    set via the ws URL query string (``?blueprint=<id>``); a per-message
    ``blueprint`` field overrides it. When neither is given, the legacy
    behaviour (server-configured OpenAI model) is preserved.

    Team compose (REQ-23) sends ``params: {team, target: "all"|memberId}``.
    Runtime for that path is stubbed until a real roster executor exists.

    Auth is Django **session** only (``AuthMiddlewareStack`` cookie). A
    Settings-page API bearer token does not authenticate this socket.
    """

    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        # Optional connection-level default blueprint (?blueprint=<id>).
        query_params = parse_qs(self.scope.get("query_string", b"").decode())
        self.default_blueprint = (query_params.get("blueprint") or [None])[0]
        self.messages = []
        # Accept before any DB/thread work. A wedged CurrentThreadExecutor
        # used to hang handshake (HANDSHAKING, never CONNECT) and loop /chat.
        await self.accept()

        try:
            if (not getattr(self.user, "is_authenticated", False)) and swarm_allow_anonymous(
                client_ip_from_scope(self.scope)
            ):
                try:
                    self.user = await database_sync_to_async(get_or_create_preview_user)()
                except Exception:
                    logger.exception(
                        "Preview user mint failed for conversation %s; keeping socket open",
                        self.conversation_id,
                    )
                    return
            if getattr(self.user, "is_authenticated", False):
                await self._send_spa_hello()
                self.active_agent = self.default_blueprint
                self._pending_tool_decisions = {}
                try:
                    self.messages = await self.fetch_conversation(self.conversation_id)
                except Exception:
                    logger.exception(
                        "fetch_conversation failed after accept; continuing with empty transcript"
                    )
                    self.messages = []
                await self._emit_suggestions_if_enabled(self.default_blueprint)
            else:
                # Close after accept so the client sees 4401 (not 1006).
                # receive() re-checks auth so anonymous clients cannot hit the LLM.
                await self.close(
                    code=WS_AUTH_REQUIRED_CODE,
                    reason="authentication required",
                )
        except Exception:
            logger.exception("post-accept websocket setup failed; socket stays open")

    async def _send_spa_hello(self):
        """Tell the tab which SPA bake this backend expects (REQ-78)."""
        try:
            from swarm.core.app_version import get_app_version

            await self.send(
                text_data=json.dumps(
                    {
                        "type": SPA_HELLO_TYPE,
                        "spa_version": get_app_version(),
                    }
                )
            )
        except Exception:
            logger.debug("spa_hello advertise failed", exc_info=True)

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
        # Auth gate: accept-then-close 4401 leaves a race where a frame can
        # land before the close is applied. Refuse unauthenticated receives
        # (do not append to transcript or invoke blueprints / LLM).
        if not getattr(self.user, "is_authenticated", False):
            if swarm_allow_anonymous(client_ip_from_scope(getattr(self, "scope", None))):
                self.user = await database_sync_to_async(get_or_create_preview_user)()
            else:
                await self.close(
                    code=WS_AUTH_REQUIRED_CODE,
                    reason="authentication required",
                )
                return
            if not getattr(self.user, "is_authenticated", False):
                await self.close(
                    code=WS_AUTH_REQUIRED_CODE,
                    reason="authentication required",
                )
                return

        # Tolerate malformed frames without killing the socket: log and drop.
        try:
            text_data_json = json.loads(text_data)
            if not isinstance(text_data_json, dict):
                raise ValueError("frame must be a JSON object")
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("Ignoring malformed chat frame (%s): %.200r", exc, text_data)
            return

        if text_data_json.get("type") == "tool_decision":
            await self.resolve_tool_decision(text_data_json)
            return

        if text_data_json.get("type") == "status":
            status_text = text_data_json.get("text")
            if not isinstance(status_text, str) or not status_text.strip():
                return
            agent = text_data_json.get("agent")
            if isinstance(agent, str) and agent.strip():
                self.active_agent = agent.strip()
            self.messages.append(
                {"role": "status", "content": status_text, "ts": _message_ts()}
            )
            conversation_id = getattr(self, "conversation_id", None)
            if conversation_id:
                await self.save_conversation(conversation_id, self.messages)
            return

        if "edit" in text_data_json:
            await self.apply_message_edit(text_data_json.get("edit"))
            return

        try:
            message_text = text_data_json["message"]
            if not isinstance(message_text, str):
                raise ValueError("'message' must be a string")
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Ignoring malformed chat frame (%s): %.200r", exc, text_data)
            return

        if not message_text.strip():
            return

        # Per-message blueprint selection wins over the connection default.
        blueprint_id = text_data_json.get("blueprint") or getattr(
            self, "default_blueprint", None
        )
        self.active_agent = blueprint_id or getattr(self, "active_agent", None)
        params = text_data_json.get("params")
        if not isinstance(params, dict):
            params = None

        if params and params.get("new_session"):
            # REQ-65: CoS/user task asked for an empty session on this socket.
            self.messages = []

        self.messages.append(
            {
                "role": "user",
                "content": message_text,
                "ts": _message_ts(),
            }
        )

        user_message_html = render_to_string(
            "websocket_partials/user_message.html",
            {"message_text": message_text},
        )
        await self.send(text_data=user_message_html)

        # REQ-92: new-session status must precede the assistant bubble on the wire.
        await self._emit_new_cli_session_notice(blueprint_id, params)

        message_id = uuid.uuid4().hex
        contents_div_id = f"message-response-{message_id}"
        system_message_html = render_to_string(
            "websocket_partials/system_message.html",
            {"contents_div_id": contents_div_id},
        )
        await self.send(text_data=system_message_html)

        if params and params.get("team"):
            await self.respond_with_team_stub(params, message_text, contents_div_id)
        elif blueprint_id:
            await self.respond_with_blueprint(blueprint_id, contents_div_id, params=params)
        else:
            await self.respond_with_default_model(contents_div_id)

    async def _emit_new_cli_session_notice(self, blueprint_id, params):
        """REQ-92: send ``Started a new {cli} session.`` before assistant_start.

        Resume / same-session turns stay quiet here. The blueprint still yields
        the honest resumed/fallback line after it knows the outcome.
        """
        try:
            from swarm.core import chat_store
            from swarm.core.chat_transcript import (
                insert_status_before_turn_assistant,
                new_cli_session_notice_if_needed,
                transcript_already_has_notice,
            )

            user_key = None
            if getattr(self.user, "is_authenticated", False):
                user_key = chat_store.user_key_for(self.user)
            thread_params = dict(params or {})
            thread_params.setdefault("agent", blueprint_id)
            thread_params.setdefault("agent_id", blueprint_id)
            thread_params.setdefault(
                "conversation_id", getattr(self, "conversation_id", "") or ""
            )
            notice = new_cli_session_notice_if_needed(
                blueprint_id=blueprint_id,
                params=thread_params,
                user_key=user_key,
            )
            if not notice or transcript_already_has_notice(self.messages, notice):
                return
            await self.send(text_data=_status_line_html(notice))
            self.messages = insert_status_before_turn_assistant(
                self.messages,
                {"role": "status", "content": notice},
            )
        except Exception:
            logger.debug("CLI new-session notice pre-emit skipped", exc_info=True)

    async def respond_with_team_stub(self, params, message_text, contents_div_id):
        """Stub team send-to-all / member-target runtime (REQ-23).

        Echoes ``[team:<id> target:<all|memberId>]`` so the compose path is
        exercisable without a multi-agent roster executor.
        """
        team = str(params.get("team") or "")
        target = str(params.get("target") or "all")
        canned = f"[team:{team} target:{target}] {message_text}"
        await self.send(text_data=_oob_append_html(contents_div_id, canned))
        self.messages.append({"role": "assistant", "content": canned})
        final_html = render_to_string(
            "websocket_partials/final_system_message.html",
            {"contents_div_id": contents_div_id, "message": canned},
        )
        await self.send(text_data=final_html)
        await self._emit_suggestions_if_enabled(None)

    async def respond_with_blueprint(self, blueprint_id, contents_div_id, params=None):
        """Generate the assistant reply by running a discovered blueprint."""
        # In test mode, skip slow blueprint instantiation and return canned output.
        if os.environ.get("SWARM_TEST_MODE"):
            from pathlib import Path as _Path

            from django.conf import settings as _settings
            bp_dir = _Path(getattr(_settings, "BLUEPRINT_DIRECTORY", "src/swarm/blueprints"))
            known = {d.name for d in bp_dir.iterdir() if d.is_dir() and not d.name.startswith("_")} if bp_dir.is_dir() else set()
            from swarm.core.cli_catalog import cli_from_rail_id
            if blueprint_id not in known and not cli_from_rail_id(blueprint_id):
                await self.send_error_message(
                    contents_div_id,
                    f"Error: blueprint '{blueprint_id}' not found.",
                )
                return
            instruction = self.messages[-1]["content"] if self.messages else ""
            canned = f"[TEST-MODE] Jeeves at your service. You said: '{instruction}'" if blueprint_id == "jeeves" else f"[TEST-MODE] {blueprint_id} at your service. You said: '{instruction}'"
            await self.send(text_data=_oob_append_html(contents_div_id, canned))
            self.messages.append({"role": "assistant", "content": canned, "ts": _message_ts()})
            final_html = render_to_string(
                "websocket_partials/final_system_message.html",
                {"contents_div_id": contents_div_id, "message": canned},
            )
            await self.send(text_data=final_html)
            await self._emit_suggestions_if_enabled(blueprint_id)
            return

        from swarm.views.chat_views import (
            _chunk_is_final,
            _extract_message_from_chunk,
        )

        try:
            from swarm.core.cli_catalog import cli_from_rail_id
            from swarm.views.utils import get_blueprint_instance

            from swarm.core.inference_list import (
                failover_notice,
                is_config_failure,
                is_rate_limit,
                normalize_inference_list,
                pick_scale_out,
                seat_id,
                seat_kind,
            )

            cli_name = None
            if isinstance(params, dict):
                raw_cli = params.get("cli")
                if isinstance(raw_cli, str) and raw_cli.strip():
                    cli_name = raw_cli.strip()
            if not cli_name:
                cli_name = cli_from_rail_id(blueprint_id)
            inference_seats = normalize_inference_list(
                params.get("inference_list") if isinstance(params, dict) else None
            )
            scale_out = bool(params and params.get("scale_out"))
            if scale_out and inference_seats:
                raw_idx = params.get("inference_index") if isinstance(params, dict) else 0
                try:
                    idx = int(raw_idx or 0)
                except (TypeError, ValueError):
                    idx = 0
                chosen = pick_scale_out(inference_seats, idx)
                inference_seats = [chosen] if chosen else []
            if str(blueprint_id).strip().lower() == "api_agent":
                run_id = "chatbot"
                blueprint_instance = await get_blueprint_instance(run_id)
                profile = None
                if isinstance(params, dict):
                    raw_model = params.get("model") or params.get("llm_profile")
                    if isinstance(raw_model, str) and raw_model.strip() and raw_model.strip() != "default":
                        profile = raw_model.strip()
                if inference_seats:
                    first = inference_seats[0]
                    if seat_kind(first) == "llm":
                        profile = seat_id(first)
                if blueprint_instance is not None and profile:
                    blueprint_instance.llm_profile_name = profile
            else:
                run_id = "cli_agent" if cli_name else blueprint_id
                if inference_seats and seat_kind(inference_seats[0]) == "cli":
                    cli_name = seat_id(inference_seats[0])
                    run_id = "cli_agent"
                blueprint_instance = await get_blueprint_instance(run_id)
                if blueprint_instance is not None and cli_name and hasattr(
                    blueprint_instance, "set_params"
                ):
                    blueprint_instance.set_params({"cli": cli_name})
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

        thread_params = {
            "conversation_id": getattr(self, "conversation_id", ""),
            "agent": blueprint_id,
            "agent_id": blueprint_id,
        }
        if getattr(self.user, "is_authenticated", False):
            try:
                from swarm.core import chat_store

                thread_params["user_key"] = chat_store.user_key_for(self.user)
            except Exception:
                logger.exception("Could not resolve chat user_key for CLI session")
        if isinstance(params, dict):
            thread_params.update(params)
        if hasattr(blueprint_instance, "set_params") and callable(blueprint_instance.set_params):
            existing = getattr(blueprint_instance, "_params", None)
            if not isinstance(existing, dict):
                existing = {}
            blueprint_instance.set_params({**existing, **thread_params})

        final_message = None
        token = None
        try:
            from swarm.core.safety import (
                SafetySession,
                channel_for_runtime,
                install_safety_session,
                safety_role_assigned,
            )

            channel = channel_for_runtime(blueprint_id=blueprint_id)
            metadata = getattr(blueprint_instance, "metadata", None)
            if not isinstance(metadata, dict):
                metadata = {}
            session = SafetySession(
                agent_id=str(blueprint_id),
                channel=channel,
                safety_assigned=safety_role_assigned(
                    getattr(blueprint_instance, "agents", None),
                    metadata=metadata,
                ),
                elicit_fn=self.elicit_tool_approval,
                emit_fn=self.emit_tool_event,
            )
            token = install_safety_session(session)
            model_messages = await _compacted_context(
                getattr(self, "conversation_id", ""),
                self.messages,
            )
            async for chunk in blueprint_instance.run(model_messages):
                if isinstance(chunk, dict) and chunk.get("type") == "cli_session_notice":
                    notice = str(chunk.get("content") or "").strip()
                    if notice:
                        from swarm.core.chat_transcript import (
                            insert_status_before_turn_assistant,
                            transcript_already_has_notice,
                        )

                        if not transcript_already_has_notice(self.messages, notice):
                            await self.send(text_data=_status_line_html(notice))
                            self.messages = insert_status_before_turn_assistant(
                                self.messages,
                                {"role": "status", "content": notice, "ts": _message_ts()},
                            )
                    continue
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
            from swarm.core.inference_list import (
                failover_notice,
                is_config_failure,
                is_rate_limit,
                normalize_inference_list,
                retry_params,
                should_failover,
            )

            seats = normalize_inference_list(
                params.get("inference_list") if isinstance(params, dict) else None
            )
            rest = seats[1:] if seats else []
            scale_out = bool(params and params.get("scale_out"))
            if should_failover(e, rest, scale_out=scale_out):
                notice = failover_notice(seats[0], rest[0])
                await self.send(text_data=_status_line_html(notice))
                self.messages.append({"role": "status", "content": notice})
                await self.respond_with_blueprint(
                    blueprint_id,
                    contents_div_id,
                    params=retry_params(params, rest),
                )
                return
            if (
                seats
                and not rest
                and not scale_out
                and is_config_failure(e)
                and not is_rate_limit(e)
            ):
                notice = failover_notice(seats[0], None, exhausted=True)
                await self.send(text_data=_status_line_html(notice))
                self.messages.append({"role": "status", "content": notice})
            await self.send_error_message(
                contents_div_id,
                f"Error: blueprint '{blueprint_id}' failed while generating a reply.",
            )
            return
        finally:
            if token is not None:
                from swarm.core.safety import reset_safety_session

                reset_safety_session(token)

        if not isinstance(final_message, dict) or final_message.get("content") is None:
            await self.send_error_message(
                contents_div_id,
                f"Error: blueprint '{blueprint_id}' did not return a reply.",
            )
            return

        from swarm.core.model_text import sanitize_model_text

        full_message = sanitize_model_text(final_message["content"])
        if not full_message:
            await self.send_error_message(
                contents_div_id,
                "Error: the model returned no usable text (empty or tokenizer leftovers).",
            )
            return
        await self.send(text_data=_oob_append_html(contents_div_id, full_message))

        self.messages.append(
            {
                "role": "assistant",
                "content": full_message,
                "ts": _message_ts(),
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
        await self._emit_suggestions_if_enabled(blueprint_id)

    async def _emit_suggestions_if_enabled(self, agent_id):
        """REQ-85: JSON chips after a finished turn (never mid-token, never in LLM context)."""
        try:
            from swarm.core.suggestions import suggestions_payload_for_turn

            target = (
                agent_id
                or getattr(self, "active_agent", None)
                or getattr(self, "default_blueprint", None)
            )
            payload = suggestions_payload_for_turn(target, getattr(self, "messages", None))
            if payload:
                await self.emit_tool_event(payload)
        except Exception:
            logger.debug("suggestions emit skipped", exc_info=True)

    async def emit_tool_event(self, payload: dict) -> None:
        """JSON tool-status / approval / PR-opened / suggestions frames for the SPA."""
        try:
            from swarm.core.pr_opened import persist_pr_opened_message

            if isinstance(payload, dict) and payload.get("type") == "pr_opened":
                opener = payload.get("opener")
                if not isinstance(opener, dict):
                    opener = {}
                    payload["opener"] = opener
                agent_id = (
                    opener.get("agent_id")
                    or getattr(self, "active_agent", None)
                    or getattr(self, "default_blueprint", None)
                    or ""
                )
                if agent_id and not opener.get("agent_id"):
                    opener["agent_id"] = str(agent_id)
                conversation_id = getattr(self, "conversation_id", None) or ""
                if conversation_id and not opener.get("conversation_id"):
                    opener["conversation_id"] = str(conversation_id)
                persist_pr_opened_message(self.messages, payload)
            await self.send(text_data=json.dumps(payload))
        except Exception:
            logger.debug("tool event send failed", exc_info=True)

    async def elicit_tool_approval(self, tool_name: str, arguments: dict) -> str:
        """Pause the API-agent run until the chat sends Allow / Always / Deny."""
        approval_id = uuid.uuid4().hex
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        pending = getattr(self, "_pending_tool_decisions", None)
        if pending is None:
            pending = {}
            self._pending_tool_decisions = pending
        pending[approval_id] = future
        await self.emit_tool_event(
            {
                "type": "tool_approval",
                "id": approval_id,
                "name": tool_name,
                "agent_id": getattr(self, "active_agent", None) or "",
                "arguments": arguments or {},
            }
        )
        try:
            decision = await asyncio.wait_for(future, timeout=300)
        except TimeoutError:
            decision = "deny"
        finally:
            pending.pop(approval_id, None)
        return str(decision or "deny")

    async def resolve_tool_decision(self, payload: dict) -> None:
        approval_id = str(payload.get("id") or "")
        decision = str(payload.get("decision") or "deny")
        pending = getattr(self, "_pending_tool_decisions", {}) or {}
        future = pending.get(approval_id)
        if future is None or future.done():
            return
        future.set_result(decision)

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
        from swarm.utils.env_utils import get_llm_base_url, openai_client_kwargs

        base_url = get_llm_base_url()
        client_kwargs = openai_client_kwargs()
        model = (
            os.environ.get("LITELLM_MODEL")
            or os.environ.get("OPENAI_MODEL")
            or os.environ.get("DEFAULT_LLM")
        )
        if not model:
            from swarm.core.llm_task_routing import model_id_for_profile, resolve_chat_model

            route = resolve_chat_model()
            model = model_id_for_profile(route.profile)
            if route.warning:
                logger.warning("Default chat model: %s", route.warning)
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
            expected = get_llm_base_url()
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

        full_message = ""
        try:
            model_messages = await _compacted_context(
                getattr(self, "conversation_id", ""),
                self.messages,
            )
            stream = await client.chat.completions.create(
                model=model,
                messages=model_messages,
                stream=True,
            )
            async for chunk in stream:
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                message_chunk = choices[0].delta.content
                if message_chunk:
                    full_message += message_chunk
                    await self.send(
                        text_data=_oob_append_html(contents_div_id, message_chunk)
                    )
        except Exception as e:
            logger.error("Default-model chat stream failed: %s", e, exc_info=True)
            await self.send_error_message(
                contents_div_id,
                "Error: the default model failed while generating a reply. "
                "Check the server's LLM configuration (LITELLM_* / OPENAI_*).",
            )
            return

        from swarm.core.model_text import sanitize_model_text

        full_message = sanitize_model_text(full_message)
        if not full_message:
            await self.send_error_message(
                contents_div_id,
                "Error: the model returned no usable text (empty or tokenizer leftovers).",
            )
            return

        self.messages.append(
            {
                "role": "assistant",
                "content": full_message,
                "ts": _message_ts(),
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
        await self._emit_suggestions_if_enabled(None)

    async def apply_message_edit(self, edit):
        """Replace one transcript turn and persist it (REQ-49)."""
        from swarm.core.agent_kind import can_edit_agent_messages

        agent = getattr(self, "active_agent", None) or getattr(self, "default_blueprint", None)
        if not can_edit_agent_messages(agent):
            logger.info("Ignoring message edit on non-API agent %s", agent)
            return
        if not isinstance(edit, dict):
            logger.warning("Ignoring malformed chat edit frame: %.200r", edit)
            return
        index = edit.get("index")
        content = edit.get("content")
        if type(index) is not int or not isinstance(content, str):
            logger.warning("Ignoring malformed chat edit frame: %.200r", edit)
            return
        if index < 0 or index >= len(self.messages):
            logger.warning(
                "Ignoring chat edit index %s (transcript length %s)",
                index,
                len(self.messages),
            )
            return
        current = dict(self.messages[index])
        current["content"] = content
        current["edited"] = True
        self.messages[index] = current
        conversation_id = getattr(self, "conversation_id", None)
        if conversation_id:
            await self.save_conversation(conversation_id, self.messages)

    @database_sync_to_async
    def fetch_conversation(self, conversation_id):
        """
        Fetch conversation messages from memory or DB. If missing from memory, load from DB.

        Always returns a COPY: two tabs sharing a conversation must not mutate
        each other's in-flight transcript list (interleaved appends previously
        corrupted both and double-persisted merged turns on disconnect).
        """
        cache_key = _conversation_cache_key(self.user, conversation_id)
        if cache_key in IN_MEMORY_CONVERSATIONS:
            return list(IN_MEMORY_CONVERSATIONS[cache_key])

        try:
            chat = ChatConversation.objects.get(conversation_id=conversation_id, student=self.user)
            messages = [{'role': m['sender'], 'content': m['content']} for m in chat.messages.values("sender", "content")]
            IN_MEMORY_CONVERSATIONS[cache_key] = messages  # Cache it
            return list(messages)
        except ChatConversation.DoesNotExist:
            logger.debug(f"Conversation {conversation_id} not found in database for user: {self.user}")

        agent_id = getattr(self, "default_blueprint", None)
        try:
            from swarm.core.agent_settings import is_new_chat_per_task

            # REQ-65: on-mode tasks must not inherit the reused agent transcript.
            if agent_id and is_new_chat_per_task(agent_id):
                disk = _load_agent_json(
                    self.user, agent_id, conversation_id=conversation_id
                )
                if disk:
                    IN_MEMORY_CONVERSATIONS[cache_key] = disk
                    return list(disk)
                return []
        except Exception:
            logger.debug("new-chat-per-task check failed; using reuse fallback", exc_info=True)

        # Disk fallback: per-agent JSON (survives a new conversation UUID).
        disk = _load_agent_json(self.user, agent_id)
        if disk:
            IN_MEMORY_CONVERSATIONS[cache_key] = disk
            return list(disk)
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
        _save_agent_json(
            self.user,
            getattr(self, "active_agent", None) or getattr(self, "default_blueprint", None),
            new_messages,
            conversation_id=conversation_id,
        )

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
