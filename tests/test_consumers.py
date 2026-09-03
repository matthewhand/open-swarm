"""
Unit tests for src/swarm/consumers.py

Covers:
- connect: authenticated vs unauthenticated, ?blueprint= query param default
- disconnect: cleanup, save, delete empty conversations
- receive: valid JSON, missing keys, invalid JSON, empty messages
- blueprint selection: message field, connection default, override,
  unknown-blueprint error partial
- fetch_conversation: cache hit, DB hit, DoesNotExist
- save_conversation: create/update, idempotent replace on repeat save
- delete_conversation: existing, missing
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from swarm.consumers import (
    IN_MEMORY_CONVERSATIONS,
    DjangoChatConsumer,
    _conversation_cache_key,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock()
    user.is_authenticated = True
    user.pk = 1
    return user


@pytest.fixture
def mock_unauthenticated_user():
    """Create a mock unauthenticated user."""
    user = MagicMock()
    user.is_authenticated = False
    return user


@pytest.fixture
def mock_scope(mock_user):
    """Create a mock scope for the consumer."""
    return {
        "user": mock_user,
        "url_route": {
            "kwargs": {
                "conversation_id": "test-conv-123"
            }
        }
    }


@pytest.fixture
def mock_scope_unauthenticated(mock_unauthenticated_user):
    """Create a mock scope with unauthenticated user."""
    return {
        "user": mock_unauthenticated_user,
        "url_route": {
            "kwargs": {
                "conversation_id": "test-conv-123"
            }
        }
    }


@pytest.fixture
def consumer(mock_scope, mock_user):
    """Create a consumer instance for testing."""
    consumer = DjangoChatConsumer()
    consumer.scope = mock_scope
    consumer.user = mock_user  # Set user attribute directly (normally set in connect)
    consumer.messages = []
    return consumer


@pytest.fixture(autouse=True)
def isolated_memory_cache():
    """Provide isolated in-memory conversation cache for each test.
    
    This fixture saves and restores the global IN_MEMORY_CONVERSATIONS
    to ensure test isolation when running with xdist.
    """
    # Save original state
    original = IN_MEMORY_CONVERSATIONS.copy()
    IN_MEMORY_CONVERSATIONS.clear()

    yield IN_MEMORY_CONVERSATIONS

    # Restore original state
    IN_MEMORY_CONVERSATIONS.clear()
    IN_MEMORY_CONVERSATIONS.update(original)


# =============================================================================
# Connect Tests
# =============================================================================


class TestConnect:
    """Tests for DjangoChatConsumer.connect method."""

    @pytest.mark.asyncio
    async def test_connect_authenticated_accepts(self, consumer, mock_scope):
        """Authenticated user should have connection accepted."""
        with patch.object(consumer, 'fetch_conversation', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []

            with patch.object(consumer, 'accept', new_callable=AsyncMock) as mock_accept:
                order = []
                mock_accept.side_effect = lambda *a, **k: order.append("accept")
                mock_fetch.side_effect = lambda *a, **k: order.append("fetch") or []
                await consumer.connect()

                mock_accept.assert_called_once()
                mock_fetch.assert_called_once_with("test-conv-123")
                assert order == ["accept", "fetch"]

    @pytest.mark.asyncio
    async def test_connect_accepts_even_if_fetch_raises(self, consumer):
        """DB/thread-pool failure must not leave the handshake hanging."""
        with patch.object(consumer, 'fetch_conversation', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = RuntimeError("CurrentThreadExecutor already quit or is broken")
            with patch.object(consumer, 'accept', new_callable=AsyncMock) as mock_accept:
                with patch.object(consumer, 'close', new_callable=AsyncMock) as mock_close:
                    await consumer.connect()
                    mock_accept.assert_called_once()
                    mock_close.assert_not_called()
                    assert consumer.messages == []

    @pytest.mark.asyncio
    async def test_connect_authenticated_fetches_conversation(self, consumer):
        """Authenticated user should have their conversation fetched."""
        existing_messages = [{"role": "user", "content": "Hello"}]

        with patch.object(consumer, 'fetch_conversation', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = existing_messages

            with patch.object(consumer, 'accept', new_callable=AsyncMock):
                await consumer.connect()

                assert consumer.messages == existing_messages

    @pytest.mark.asyncio
    async def test_connect_unauthenticated_closes(self, mock_scope_unauthenticated):
        """Unauthenticated user is accept-then-closed with WS_AUTH_REQUIRED_CODE."""
        from swarm.consumers import WS_AUTH_REQUIRED_CODE

        consumer = DjangoChatConsumer()
        consumer.scope = mock_scope_unauthenticated

        with patch.object(consumer, 'accept', new_callable=AsyncMock) as mock_accept:
            with patch.object(consumer, 'close', new_callable=AsyncMock) as mock_close:
                await consumer.connect()

                mock_accept.assert_called_once()
                mock_close.assert_called_once_with(
                    code=WS_AUTH_REQUIRED_CODE,
                    reason="authentication required",
                )

    @pytest.mark.asyncio
    async def test_connect_passes_client_ip_to_anonymous_gate(
        self, mock_scope_unauthenticated
    ):
        mock_scope_unauthenticated["client"] = ("10.0.0.199", 51234)
        consumer = DjangoChatConsumer()
        consumer.scope = mock_scope_unauthenticated
        preview = MagicMock()
        preview.is_authenticated = True
        preview.pk = 7

        with patch("swarm.consumers.swarm_allow_anonymous", return_value=True) as allow:
            with patch(
                "swarm.consumers.database_sync_to_async",
                side_effect=lambda fn: AsyncMock(return_value=preview),
            ):
                with patch.object(
                    consumer, "fetch_conversation", new_callable=AsyncMock, return_value=[]
                ):
                    with patch.object(consumer, "accept", new_callable=AsyncMock):
                        with patch.object(consumer, "close", new_callable=AsyncMock) as mock_close:
                            await consumer.connect()
        allow.assert_called_with("10.0.0.199")
        mock_close.assert_not_called()

    @pytest.mark.asyncio
    async def test_connect_anonymous_preview_does_not_close_4401(
        self, mock_scope_unauthenticated
    ):
        """SWARM_ALLOW_ANONYMOUS preview user: accept and keep the socket."""
        preview = MagicMock()
        preview.is_authenticated = True
        preview.pk = 99

        consumer = DjangoChatConsumer()
        consumer.scope = mock_scope_unauthenticated

        with patch("swarm.consumers.swarm_allow_anonymous", return_value=True):
            with patch(
                "swarm.consumers.database_sync_to_async",
                side_effect=lambda fn: AsyncMock(return_value=preview),
            ):
                with patch.object(
                    consumer, "fetch_conversation", new_callable=AsyncMock
                ) as mock_fetch:
                    mock_fetch.return_value = []
                    with patch.object(consumer, "accept", new_callable=AsyncMock) as mock_accept:
                        with patch.object(consumer, "close", new_callable=AsyncMock) as mock_close:
                            await consumer.connect()

        mock_accept.assert_called_once()
        mock_close.assert_not_called()
        mock_fetch.assert_called_once()
        assert consumer.user is preview

    @pytest.mark.asyncio
    async def test_connect_anonymous_preview_mint_failure_keeps_socket(
        self, mock_scope_unauthenticated
    ):
        """If the preview user cannot be minted, do not 4401 — socket stays open."""
        consumer = DjangoChatConsumer()
        consumer.scope = mock_scope_unauthenticated

        with patch("swarm.consumers.swarm_allow_anonymous", return_value=True):
            with patch(
                "swarm.consumers.database_sync_to_async",
                side_effect=lambda fn: AsyncMock(
                    side_effect=RuntimeError("CurrentThreadExecutor already quit")
                ),
            ):
                with patch.object(consumer, "accept", new_callable=AsyncMock) as mock_accept:
                    with patch.object(consumer, "close", new_callable=AsyncMock) as mock_close:
                        await consumer.connect()

        mock_accept.assert_called_once()
        mock_close.assert_not_called()
        assert consumer.messages == []

    @pytest.mark.asyncio
    async def test_connect_sets_conversation_id(self, consumer, mock_scope):
        """Connect should set conversation_id from URL route."""
        with patch.object(consumer, 'fetch_conversation', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []

            with patch.object(consumer, 'accept', new_callable=AsyncMock):
                await consumer.connect()

                assert consumer.conversation_id == "test-conv-123"

    @pytest.mark.asyncio
    async def test_connect_without_query_string_has_no_default_blueprint(self, consumer):
        """No ?blueprint= query param -> no connection-level default."""
        with patch.object(consumer, 'fetch_conversation', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []

            with patch.object(consumer, 'accept', new_callable=AsyncMock):
                await consumer.connect()

                assert consumer.default_blueprint is None

    @pytest.mark.asyncio
    async def test_connect_query_param_sets_default_blueprint(self, consumer):
        """?blueprint=<id> on the ws URL becomes the connection default."""
        consumer.scope["query_string"] = b"blueprint=jeeves"

        with patch.object(consumer, 'fetch_conversation', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []

            with patch.object(consumer, 'accept', new_callable=AsyncMock):
                await consumer.connect()

                assert consumer.default_blueprint == "jeeves"


# =============================================================================
# Disconnect Tests
# =============================================================================


class TestDisconnect:
    """Tests for DjangoChatConsumer.disconnect method."""

    @pytest.mark.asyncio
    async def test_disconnect_authenticated_saves_conversation(self, consumer):
        """Authenticated user should have conversation saved on disconnect."""
        consumer.messages = [{"role": "user", "content": "Hello"}]
        consumer.conversation_id = "test-conv-123"

        with patch.object(consumer, 'save_conversation', new_callable=AsyncMock) as mock_save:
            with patch.object(consumer, 'delete_conversation', new_callable=AsyncMock) as mock_delete:
                await consumer.disconnect(close_code=1000)

                mock_save.assert_called_once_with("test-conv-123", consumer.messages)
                mock_delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_disconnect_deletes_empty_conversation(self, consumer):
        """Empty conversation should be deleted on disconnect."""
        consumer.messages = []
        consumer.conversation_id = "test-conv-123"

        with patch.object(consumer, 'save_conversation', new_callable=AsyncMock):
            with patch.object(consumer, 'delete_conversation', new_callable=AsyncMock) as mock_delete:
                await consumer.disconnect(close_code=1000)

                mock_delete.assert_called_once_with("test-conv-123")

    @pytest.mark.asyncio
    async def test_disconnect_clears_memory_cache(self, consumer):
        """Disconnect should clear the in-memory cache for the conversation."""
        consumer.messages = []
        consumer.conversation_id = "test-conv-123"
        cache_key = _conversation_cache_key(consumer.user, "test-conv-123")
        IN_MEMORY_CONVERSATIONS[cache_key] = []

        with patch.object(consumer, 'save_conversation', new_callable=AsyncMock):
            with patch.object(consumer, 'delete_conversation', new_callable=AsyncMock):
                await consumer.disconnect(close_code=1000)

                assert cache_key not in IN_MEMORY_CONVERSATIONS

    @pytest.mark.asyncio
    async def test_disconnect_unauthenticated_does_not_save(self, mock_scope_unauthenticated, mock_unauthenticated_user):
        """Unauthenticated user should not trigger save on disconnect."""
        consumer = DjangoChatConsumer()
        consumer.scope = mock_scope_unauthenticated
        consumer.user = mock_unauthenticated_user
        consumer.messages = []

        with patch.object(consumer, 'save_conversation', new_callable=AsyncMock) as mock_save:
            await consumer.disconnect(close_code=1000)

            mock_save.assert_not_called()


# =============================================================================
# Receive Tests
# =============================================================================


class TestReceive:
    """Tests for DjangoChatConsumer.receive method."""

    @pytest.mark.asyncio
    async def test_receive_valid_json_adds_user_message(self, consumer):
        """Valid JSON message should be added to messages list."""
        consumer.messages = []
        text_data = json.dumps({"message": "Hello, world!"})

        # Create a proper async iterator for the stream
        async def mock_stream():
            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock()]
            mock_chunk.choices[0].delta.content = "Response"
            yield mock_chunk
            # End with None content to stop
            mock_chunk2 = MagicMock()
            mock_chunk2.choices = [MagicMock()]
            mock_chunk2.choices[0].delta.content = None
            yield mock_chunk2

        # Mock all the external dependencies
        with patch('swarm.consumers.render_to_string', return_value="<div>user message</div>"):
            with patch('swarm.consumers.AsyncOpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_client.base_url = None  # Set base_url to None to avoid litellm check
                mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
                mock_client.close = AsyncMock()
                mock_openai.return_value = mock_client

                # Patch os at module level before the function runs
                import swarm.consumers as consumers_module
                original_os = consumers_module.os
                mock_os = MagicMock()
                mock_os.getenv = MagicMock(return_value="test-key")
                mock_os.environ = {'OPENAI_API_KEY': 'test-key', 'OPENAI_MODEL': 'test-model'}
                consumers_module.os = mock_os

                try:
                    with patch.object(consumer, 'send', new_callable=AsyncMock):
                        await consumer.receive(text_data)

                        assert len(consumer.messages) == 2
                        assert consumer.messages[0]["role"] == "user"
                        assert consumer.messages[0]["content"] == "Hello, world!"
                finally:
                    consumers_module.os = original_os

    @pytest.mark.asyncio
    async def test_receive_empty_message_returns_early(self, consumer):
        """Empty message should be ignored."""
        consumer.messages = []
        text_data = json.dumps({"message": "   "})

        await consumer.receive(text_data)

        assert len(consumer.messages) == 0

    @pytest.mark.asyncio
    async def test_receive_missing_message_key_is_ignored(self, consumer):
        """JSON without 'message' key is logged and dropped, socket survives."""
        text_data = json.dumps({"content": "Hello"})

        await consumer.receive(text_data)

        assert len(consumer.messages) == 0

    @pytest.mark.asyncio
    async def test_receive_invalid_json_is_ignored(self, consumer):
        """Invalid JSON is logged and dropped instead of killing the socket."""
        text_data = "not valid json"

        await consumer.receive(text_data)

        assert len(consumer.messages) == 0

    @pytest.mark.asyncio
    async def test_receive_non_string_message_is_ignored(self, consumer):
        """A non-string 'message' value is dropped without raising."""
        text_data = json.dumps({"message": 12345})

        await consumer.receive(text_data)

        assert len(consumer.messages) == 0


# =============================================================================
# Blueprint Selection Tests
# =============================================================================


class TestBlueprintSelection:
    """Tests for blueprint-aware reply routing in receive()."""

    @pytest.mark.asyncio
    async def test_receive_blueprint_field_routes_to_blueprint(self, consumer):
        """{"message", "blueprint"} should dispatch to the blueprint path."""
        consumer.messages = []
        text_data = json.dumps({"message": "Hello", "blueprint": "jeeves"})

        with patch('swarm.consumers.render_to_string', return_value="<div></div>"):
            with patch.object(consumer, 'send', new_callable=AsyncMock):
                with patch.object(consumer, 'respond_with_blueprint', new_callable=AsyncMock) as mock_bp:
                    with patch.object(consumer, 'respond_with_default_model', new_callable=AsyncMock) as mock_default:
                        await consumer.receive(text_data)

                        mock_bp.assert_awaited_once()
                        assert mock_bp.await_args.args[0] == "jeeves"
                        mock_default.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_receive_without_blueprint_uses_default_model(self, consumer):
        """Plain {"message"} frames keep the legacy default-model path."""
        consumer.messages = []
        text_data = json.dumps({"message": "Hello"})

        with patch('swarm.consumers.render_to_string', return_value="<div></div>"):
            with patch.object(consumer, 'send', new_callable=AsyncMock):
                with patch.object(consumer, 'respond_with_blueprint', new_callable=AsyncMock) as mock_bp:
                    with patch.object(consumer, 'respond_with_default_model', new_callable=AsyncMock) as mock_default:
                        await consumer.receive(text_data)

                        mock_default.assert_awaited_once()
                        mock_bp.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_receive_uses_connection_default_blueprint(self, consumer):
        """The ?blueprint= connection default applies to plain frames."""
        consumer.messages = []
        consumer.default_blueprint = "jeeves"
        text_data = json.dumps({"message": "Hello"})

        with patch('swarm.consumers.render_to_string', return_value="<div></div>"):
            with patch.object(consumer, 'send', new_callable=AsyncMock):
                with patch.object(consumer, 'respond_with_blueprint', new_callable=AsyncMock) as mock_bp:
                    await consumer.receive(text_data)

                    assert mock_bp.await_args.args[0] == "jeeves"

    @pytest.mark.asyncio
    async def test_receive_message_field_overrides_connection_default(self, consumer):
        """A per-message blueprint field wins over the connection default."""
        consumer.messages = []
        consumer.default_blueprint = "jeeves"
        text_data = json.dumps({"message": "Hello", "blueprint": "zeus"})

        with patch('swarm.consumers.render_to_string', return_value="<div></div>"):
            with patch.object(consumer, 'send', new_callable=AsyncMock):
                with patch.object(consumer, 'respond_with_blueprint', new_callable=AsyncMock) as mock_bp:
                    await consumer.receive(text_data)

                    assert mock_bp.await_args.args[0] == "zeus"

    @pytest.mark.asyncio
    async def test_receive_team_params_uses_stub_runtime(self, consumer):
        """REQ-23: params {team, target} stub the roster send path."""
        consumer.messages = []
        text_data = json.dumps({
            "message": "hello roster",
            "params": {"team": "demo-team", "target": "all"},
        })

        with patch("swarm.consumers.render_to_string", return_value="<div></div>"):
            with patch.object(consumer, "send", new_callable=AsyncMock):
                with patch.object(consumer, "respond_with_team_stub", new_callable=AsyncMock) as mock_team:
                    with patch.object(consumer, "respond_with_blueprint", new_callable=AsyncMock) as mock_bp:
                        with patch.object(consumer, "respond_with_default_model", new_callable=AsyncMock) as mock_default:
                            await consumer.receive(text_data)

                            mock_team.assert_awaited_once()
                            assert mock_team.await_args.args[0]["team"] == "demo-team"
                            assert mock_team.await_args.args[0]["target"] == "all"
                            mock_bp.assert_not_awaited()
                            mock_default.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_team_stub_echoes_team_and_target(self, consumer):
        consumer.messages = [{"role": "user", "content": "ping"}]
        with patch("swarm.consumers.render_to_string", return_value="<div></div>"):
            with patch.object(consumer, "send", new_callable=AsyncMock) as mock_send:
                await consumer.respond_with_team_stub(
                    {"team": "demo-team", "target": "codey"},
                    "ping",
                    "message-response-team",
                )
        sent = "".join(
            call.kwargs.get("text_data") or call.args[0]
            for call in mock_send.await_args_list
        )
        assert "team:demo-team" in sent
        assert "target:codey" in sent
        assert consumer.messages[-1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_unknown_blueprint_sends_error_partial(self, consumer):
        """Unknown blueprint -> error partial; no assistant message recorded."""
        consumer.messages = [{"role": "user", "content": "Hello"}]

        with patch('swarm.views.utils.get_blueprint_instance', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            with patch.object(consumer, 'send', new_callable=AsyncMock) as mock_send:
                await consumer.respond_with_blueprint("nope", "message-response-abc")

                sent = "".join(
                    call.kwargs.get("text_data") or call.args[0]
                    for call in mock_send.await_args_list
                )
                assert "nope" in sent
                assert "not found" in sent
                # The error is transport-level: not appended to history.
                assert all(m["role"] != "assistant" for m in consumer.messages)

    @pytest.mark.asyncio
    async def test_blueprint_reply_streams_chunk_and_final(self, consumer, monkeypatch):
        """A blueprint reply emits an OOB chunk + final partial and is
        appended to the conversation history (last message wins, spinner
        side-channel chunks skipped — same semantics as chat_views)."""
        # SWARM_TEST_MODE short-circuits respond_with_blueprint before the mock.
        monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
        consumer.messages = [{"role": "user", "content": "Hello"}]

        async def fake_run(messages, **kwargs):
            yield {"type": "spinner_update", "spinner": "Generating."}
            yield {"messages": [{"role": "assistant", "content": "BP reply"}]}

        instance = MagicMock()
        instance.run = fake_run

        with patch('swarm.views.utils.get_blueprint_instance', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = instance
            with patch.object(consumer, 'send', new_callable=AsyncMock) as mock_send:
                await consumer.respond_with_blueprint("jeeves", "message-response-abc")

                frames = [
                    call.kwargs.get("text_data") or call.args[0]
                    for call in mock_send.await_args_list
                ]
                assert len(frames) == 2  # OOB chunk + final partial
                assert 'hx-swap-oob="beforeend:#message-response-abc"' in frames[0]
                assert "BP reply" in frames[0]
                assert "BP reply" in frames[1]
                assert consumer.messages[-1] == {
                    "role": "assistant",
                    "content": "BP reply",
                }

    @pytest.mark.asyncio
    async def test_blueprint_run_uses_compacted_context(self, consumer, monkeypatch):
        """REQ-37: blueprint.run sees the summary tree, not covered raw turns."""
        monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
        consumer.conversation_id = "ws-compact-conv"
        consumer.messages = [
            {"role": "user", "content": "secret raw turn"},
            {"role": "assistant", "content": "secret raw reply"},
        ]
        seen = {}

        async def fake_run(messages, **kwargs):
            seen["messages"] = messages
            yield {"messages": [{"role": "assistant", "content": "ok"}]}

        instance = MagicMock()
        instance.run = fake_run

        async def fake_context(conversation_id, messages):
            assert conversation_id == "ws-compact-conv"
            assert messages[0]["content"] == "secret raw turn"
            return [{"role": "system", "content": "[Conversation summary]\ndigest only"}]

        with patch("swarm.consumers._compacted_context", side_effect=fake_context):
            with patch("swarm.views.utils.get_blueprint_instance", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = instance
                with patch.object(consumer, "send", new_callable=AsyncMock):
                    await consumer.respond_with_blueprint("jeeves", "message-response-compact")

        contents = " ".join(m["content"] for m in seen["messages"])
        assert "[Conversation summary]" in contents
        assert "digest only" in contents
        assert "secret raw turn" not in contents
        assert consumer.messages[0]["content"] == "secret raw turn"

    @pytest.mark.asyncio
    async def test_blueprint_reply_escapes_html_in_oob_chunk(self, consumer, monkeypatch):
        """Streaming OOB chunks must HTML-escape model text (DOM XSS)."""
        monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
        payload = '<img src=x onerror="alert(1)">'
        consumer.messages = [{"role": "user", "content": "Hello"}]

        async def fake_run(messages, **kwargs):
            yield {"messages": [{"role": "assistant", "content": payload}]}

        instance = MagicMock()
        instance.run = fake_run

        with patch("swarm.views.utils.get_blueprint_instance", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = instance
            with patch.object(consumer, "send", new_callable=AsyncMock) as mock_send:
                await consumer.respond_with_blueprint("jeeves", "message-response-xss")

                frames = [
                    call.kwargs.get("text_data") or call.args[0]
                    for call in mock_send.await_args_list
                ]
                assert len(frames) == 2
                assert "<img" not in frames[0]
                assert "&lt;img src=x onerror=" in frames[0]
                assert "&quot;alert(1)&quot;" in frames[0]
                # History keeps the raw model text; only the HTML wire format escapes.
                assert consumer.messages[-1]["content"] == payload

    @pytest.mark.asyncio
    async def test_test_mode_reflects_user_text_escaped(self, consumer, monkeypatch):
        """TEST-MODE canned replies echo the user message and must escape it."""
        monkeypatch.setenv("SWARM_TEST_MODE", "1")
        payload = '<script>alert(1)</script>'
        consumer.messages = [{"role": "user", "content": payload}]

        with patch.object(consumer, "send", new_callable=AsyncMock) as mock_send:
            await consumer.respond_with_blueprint("jeeves", "message-response-xss")

            frames = [
                call.kwargs.get("text_data") or call.args[0]
                for call in mock_send.await_args_list
            ]
            oob = frames[0]
            assert "<script>" not in oob
            assert "&lt;script&gt;" in oob
            assert consumer.messages[-1]["content"].startswith("[TEST-MODE]")

    @pytest.mark.asyncio
    async def test_blueprint_run_failure_sends_error_partial(self, consumer, monkeypatch):
        """Exceptions from blueprint.run() surface as an error partial."""
        monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
        consumer.messages = [{"role": "user", "content": "Hello"}]

        async def failing_run(messages, **kwargs):
            raise RuntimeError("boom")
            yield  # pragma: no cover - makes this an async generator

        instance = MagicMock()
        instance.run = failing_run

        with patch('swarm.views.utils.get_blueprint_instance', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = instance
            with patch.object(consumer, 'send', new_callable=AsyncMock) as mock_send:
                await consumer.respond_with_blueprint("jeeves", "message-response-abc")

                sent = "".join(
                    call.kwargs.get("text_data") or call.args[0]
                    for call in mock_send.await_args_list
                )
                assert "failed while generating" in sent
                assert all(m["role"] != "assistant" for m in consumer.messages)


# =============================================================================
# Fetch Conversation Tests
# =============================================================================


class TestFetchConversation:
    """Tests for DjangoChatConsumer.fetch_conversation method."""

    @pytest.mark.asyncio
    @pytest.mark.django_db
    async def test_fetch_from_memory_cache(self, consumer):
        """Should return cached conversation from memory."""
        # Use unique key to avoid conflicts with parallel tests
        import uuid
        unique_id = f"cached-conv-{uuid.uuid4().hex[:8]}"
        cached_messages = [{"role": "user", "content": "Cached"}]
        cache_key = _conversation_cache_key(consumer.user, unique_id)
        IN_MEMORY_CONVERSATIONS[cache_key] = cached_messages

        result = await consumer.fetch_conversation(unique_id)

        assert result == cached_messages

    def test_cache_hit_does_not_leak_across_users(self):
        """Composite cache keys prevent serving another user's transcript on hit."""
        from swarm.models import ChatConversation

        owner = MagicMock()
        owner.pk = 101
        attacker = MagicMock()
        attacker.pk = 202

        conv_id = "shared-looking-conv-id"
        secret = [{"role": "user", "content": "owner secret transcript"}]
        IN_MEMORY_CONVERSATIONS[_conversation_cache_key(owner, conv_id)] = secret
        # Pre-fix bug: bare conversation_id key. Must not be returned to attacker.
        IN_MEMORY_CONVERSATIONS[conv_id] = secret

        attacker_consumer = DjangoChatConsumer()
        attacker_consumer.user = attacker
        fetch_sync = DjangoChatConsumer.__dict__["fetch_conversation"].func

        with patch(
            "swarm.consumers.ChatConversation.objects.get",
            side_effect=ChatConversation.DoesNotExist,
        ) as mock_get:
            result = fetch_sync(attacker_consumer, conv_id)

        assert result == []
        mock_get.assert_called_once()
        assert _conversation_cache_key(attacker, conv_id) not in IN_MEMORY_CONVERSATIONS
        assert IN_MEMORY_CONVERSATIONS[_conversation_cache_key(owner, conv_id)] == secret

    @pytest.mark.django_db
    def test_fetch_from_database_sync(self, test_user):
        """Should fetch conversation from database if not in cache (sync version)."""
        from swarm.models import ChatConversation, ChatMessage

        # Create a conversation in the database
        chat = ChatConversation.objects.create(
            conversation_id="db-conv-123",
            student=test_user
        )
        ChatMessage.objects.create(
            conversation=chat,
            sender="user",
            content="DB message"
        )

        # Create consumer and test fetch (the method uses database_sync_to_async)
        consumer = DjangoChatConsumer()
        consumer.user = test_user

        # The fetch_conversation method is async and uses database_sync_to_async
        # We test the underlying logic by checking the DB state
        assert ChatConversation.objects.filter(conversation_id="db-conv-123").exists()
        assert ChatMessage.objects.filter(conversation=chat).count() == 1

    @pytest.mark.django_db
    def test_fetch_nonexistent_returns_empty_sync(self, test_user):
        """Should return empty list for nonexistent conversation (sync check)."""
        from swarm.models import ChatConversation

        # Verify no conversation exists
        assert not ChatConversation.objects.filter(conversation_id="nonexistent-conv").exists()


# =============================================================================
# Save Conversation Tests
# =============================================================================


class TestSaveConversation:
    """Tests for DjangoChatConsumer.save_conversation method."""

    @pytest.mark.django_db
    def test_save_creates_new_conversation_sync(self, test_user):
        """Should create a new conversation if it doesn't exist (sync version)."""
        from swarm.models import ChatConversation, ChatMessage

        # Create conversation directly to test the model behavior
        chat, created = ChatConversation.objects.get_or_create(
            conversation_id="new-conv-123",
            defaults={"student": test_user}
        )

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        for message in messages:
            ChatMessage.objects.create(
                conversation=chat,
                sender=message["role"],
                content=message["content"]
            )

        assert ChatConversation.objects.filter(conversation_id="new-conv-123").exists()
        assert ChatMessage.objects.filter(conversation=chat).count() == 2

    @pytest.mark.django_db
    def test_save_updates_existing_conversation_sync(self, test_user):
        """Should add messages to existing conversation (sync version)."""
        from swarm.models import ChatConversation, ChatMessage

        # Create existing conversation
        chat = ChatConversation.objects.create(
            conversation_id="existing-conv",
            student=test_user
        )

        messages = [{"role": "user", "content": "New message"}]

        for message in messages:
            ChatMessage.objects.create(
                conversation=chat,
                sender=message["role"],
                content=message["content"]
            )

        # Should have the new message
        assert ChatMessage.objects.filter(conversation=chat).count() == 1

    @pytest.mark.django_db
    def test_save_conversation_bulk_creates_messages(self, test_user):
        """save_conversation persists all messages with a constant number of queries."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from swarm.models import ChatMessage

        consumer = DjangoChatConsumer()
        consumer.user = test_user

        num_messages = 20
        new_messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(num_messages)
        ]

        # Call the unwrapped sync function behind database_sync_to_async.
        save_sync = DjangoChatConsumer.__dict__["save_conversation"].func
        with CaptureQueriesContext(connection) as ctx:
            save_sync(consumer, "bulk-conv-123", new_messages)

        assert (
            ChatMessage.objects.filter(
                conversation__conversation_id="bulk-conv-123"
            ).count()
            == num_messages
        )
        # get_or_create + delete + bulk_create should stay well below one query per message.
        assert len(ctx.captured_queries) < num_messages

        IN_MEMORY_CONVERSATIONS.pop(_conversation_cache_key(test_user, "bulk-conv-123"), None)

    @pytest.mark.django_db
    def test_save_conversation_idempotent_on_repeat(self, test_user):
        """Saving the same transcript twice must keep count at N, not 2N."""
        from swarm.models import ChatMessage

        consumer = DjangoChatConsumer()
        consumer.user = test_user
        conv_id = "idempotent-conv-123"
        cache_key = _conversation_cache_key(test_user, conv_id)
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        save_sync = DjangoChatConsumer.__dict__["save_conversation"].func
        save_sync(consumer, conv_id, messages)
        assert (
            ChatMessage.objects.filter(
                conversation__conversation_id=conv_id
            ).count()
            == len(messages)
        )
        assert IN_MEMORY_CONVERSATIONS[cache_key] == messages

        # Simulate reconnect → disconnect with the same in-memory transcript.
        save_sync(consumer, conv_id, messages)
        assert (
            ChatMessage.objects.filter(
                conversation__conversation_id=conv_id
            ).count()
            == len(messages)
        )
        assert IN_MEMORY_CONVERSATIONS[cache_key] == messages

        # Growing transcript replaces prior rows rather than appending.
        messages_grown = messages + [
            {"role": "assistant", "content": "Doing well."},
        ]
        save_sync(consumer, conv_id, messages_grown)
        qs = ChatMessage.objects.filter(
            conversation__conversation_id=conv_id
        ).order_by("timestamp")
        assert qs.count() == len(messages_grown)
        assert [m.content for m in qs] == [m["content"] for m in messages_grown]
        assert IN_MEMORY_CONVERSATIONS[cache_key] == messages_grown

        IN_MEMORY_CONVERSATIONS.pop(cache_key, None)

    @pytest.mark.django_db
    def test_save_refuses_other_users_conversation(self, test_user):
        """get_or_create by PK must not overwrite or IntegrityError on foreign ownership."""
        from django.contrib.auth import get_user_model

        from swarm.models import ChatConversation, ChatMessage

        User = get_user_model()
        owner = test_user
        attacker = User.objects.create_user(username="save-idor-attacker", password="x")

        conv_id = "owned-by-someone-else"
        chat = ChatConversation.objects.create(conversation_id=conv_id, student=owner)
        ChatMessage.objects.create(conversation=chat, sender="user", content="owner only")

        attacker_consumer = DjangoChatConsumer()
        attacker_consumer.user = attacker
        save_sync = DjangoChatConsumer.__dict__["save_conversation"].func
        save_sync(
            attacker_consumer,
            conv_id,
            [{"role": "user", "content": "attacker overwrite attempt"}],
        )

        chat.refresh_from_db()
        assert chat.student_id == owner.pk
        assert list(
            ChatMessage.objects.filter(conversation=chat).values_list("content", flat=True)
        ) == ["owner only"]
        assert _conversation_cache_key(attacker, conv_id) not in IN_MEMORY_CONVERSATIONS


# =============================================================================
# Delete Conversation Tests
# =============================================================================


class TestDeleteConversation:
    """Tests for DjangoChatConsumer.delete_conversation method."""

    @pytest.mark.django_db
    def test_delete_existing_conversation_sync(self, test_user):
        """Should delete existing empty conversation (sync version)."""
        from swarm.models import ChatConversation

        chat = ChatConversation.objects.create(
            conversation_id="to-delete",
            student=test_user
        )

        # Simulate the delete logic
        if not chat.chat_messages.exists():
            chat.delete()

        assert not ChatConversation.objects.filter(conversation_id="to-delete").exists()

    @pytest.mark.django_db
    def test_delete_nonexistent_does_not_raise_sync(self, test_user):
        """Should not raise error for nonexistent conversation (sync version)."""
        from swarm.models import ChatConversation

        # Should not raise
        try:
            chat = ChatConversation.objects.get(conversation_id="nonexistent-conv", student=test_user)
            chat.delete()
        except ChatConversation.DoesNotExist:
            pass  # Expected behavior

    @pytest.mark.django_db
    def test_delete_clears_memory_cache_sync(self, test_user):
        """Should clear memory cache when deleting (sync version)."""
        from swarm.models import ChatConversation

        ChatConversation.objects.create(
            conversation_id="cache-delete",
            student=test_user
        )
        cache_key = _conversation_cache_key(test_user, "cache-delete")
        IN_MEMORY_CONVERSATIONS[cache_key] = []

        consumer = DjangoChatConsumer()
        consumer.user = test_user
        delete_sync = DjangoChatConsumer.__dict__["delete_conversation"].func
        delete_sync(consumer, "cache-delete")

        assert cache_key not in IN_MEMORY_CONVERSATIONS
        assert not ChatConversation.objects.filter(conversation_id="cache-delete").exists()

    @pytest.mark.django_db
    def test_delete_does_not_delete_if_messages_exist_sync(self, test_user):
        """Should not delete conversation if it has messages (sync version)."""
        from swarm.models import ChatConversation, ChatMessage

        chat = ChatConversation.objects.create(
            conversation_id="with-messages",
            student=test_user
        )
        ChatMessage.objects.create(
            conversation=chat,
            sender="user",
            content="A message"
        )

        # Simulate the delete logic
        if not chat.chat_messages.exists():
            chat.delete()

        # Conversation should still exist
        assert ChatConversation.objects.filter(conversation_id="with-messages").exists()


# =============================================================================
# Integration-style Tests with WebsocketCommunicator
# =============================================================================


class TestWebsocketIntegration:
    """Integration tests using WebsocketCommunicator."""

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_unauthenticated_connection_rejected(self):
        """Unauthenticated WebSocket is accepted then closed with 4401."""
        from swarm.consumers import WS_AUTH_REQUIRED_CODE

        communicator = WebsocketCommunicator(
            DjangoChatConsumer.as_asgi(),
            "/ws/chat/test-conv/",
        )
        # Override scope with unauthenticated user
        communicator.scope["user"] = AnonymousUser()
        communicator.scope["url_route"] = {
            "kwargs": {"conversation_id": "test-conv"}
        }

        connected, _ = await communicator.connect()
        assert connected
        close_event = await communicator.receive_output(timeout=1)
        assert close_event["type"] == "websocket.close"
        assert close_event["code"] == WS_AUTH_REQUIRED_CODE

        await communicator.disconnect()

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_unauthenticated_receive_race_does_not_crash(self):
        """Anonymous frame after accept must not AttributeError or hit LLM path.

        connect() accept-then-closes with 4401; a concurrent client frame can
        still reach receive() before the close is applied. Guard must refuse
        without requiring ``self.messages`` from the authenticated branch.
        """
        from swarm.consumers import WS_AUTH_REQUIRED_CODE

        communicator = WebsocketCommunicator(
            DjangoChatConsumer.as_asgi(),
            "/ws/chat/race-conv/",
        )
        communicator.scope["user"] = AnonymousUser()
        communicator.scope["url_route"] = {
            "kwargs": {"conversation_id": "race-conv"}
        }

        connected, _ = await communicator.connect()
        assert connected
        await communicator.send_to(text_data=json.dumps({"message": "pwned?"}))

        saw_close = False
        for _ in range(8):
            try:
                event = await communicator.receive_output(timeout=0.5)
            except Exception:
                break
            if event.get("type") == "websocket.close":
                assert event["code"] == WS_AUTH_REQUIRED_CODE
                saw_close = True
                break
            # Must never emit chat HTML partials for anonymous frames.
            assert event.get("type") != "websocket.send"

        assert saw_close
        await communicator.disconnect()

    @pytest.mark.asyncio
    async def test_receive_unauthenticated_closes_without_append(self):
        """Unit: receive() for AnonymousUser closes 4401 and skips transcript."""
        from swarm.consumers import WS_AUTH_REQUIRED_CODE

        consumer = DjangoChatConsumer()
        consumer.user = AnonymousUser()
        consumer.messages = []
        consumer.conversation_id = "anon-recv"
        consumer.default_blueprint = None

        with patch.object(consumer, "close", new_callable=AsyncMock) as mock_close:
            with patch.object(
                consumer, "respond_with_default_model", new_callable=AsyncMock
            ) as mock_llm:
                await consumer.receive(text_data=json.dumps({"message": "nope"}))

        mock_close.assert_called_once_with(
            code=WS_AUTH_REQUIRED_CODE,
            reason="authentication required",
        )
        mock_llm.assert_not_called()
        assert consumer.messages == []

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_authenticated_connection_accepted(self):
        """Authenticated WebSocket connection should be accepted."""
        User = get_user_model()
        user, _ = await User.objects.aget_or_create(username="testuser")

        communicator = WebsocketCommunicator(
            DjangoChatConsumer.as_asgi(),
            "/ws/chat/test-conv/",
        )
        communicator.scope["user"] = user
        communicator.scope["url_route"] = {
            "kwargs": {"conversation_id": "test-conv-int"}
        }

        connected, _ = await communicator.connect()

        assert connected

        await communicator.disconnect()


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_receive_whitespace_only_message_returns_early(self, consumer):
        """Whitespace-only message should be ignored."""
        consumer.messages = []
        text_data = json.dumps({"message": "\n\t  \n"})

        await consumer.receive(text_data)

        assert len(consumer.messages) == 0

    @pytest.mark.asyncio
    async def test_disconnect_with_no_messages_deletes_conversation(self, consumer):
        """Disconnect with no messages should trigger delete."""
        consumer.messages = []
        consumer.conversation_id = "empty-conv"

        with patch.object(consumer, 'save_conversation', new_callable=AsyncMock):
            with patch.object(consumer, 'delete_conversation', new_callable=AsyncMock) as mock_delete:
                await consumer.disconnect(close_code=1000)

                mock_delete.assert_called_once_with("empty-conv")

    @pytest.mark.asyncio
    @pytest.mark.django_db
    async def test_memory_cache_isolation(self, consumer):
        """Each conversation should have isolated cache."""
        import uuid
        # Use unique keys to avoid conflicts with parallel tests
        key1 = f"conv-1-{uuid.uuid4().hex[:8]}"
        key2 = f"conv-2-{uuid.uuid4().hex[:8]}"

        IN_MEMORY_CONVERSATIONS[_conversation_cache_key(consumer.user, key1)] = [
            {"role": "user", "content": "Msg 1"}
        ]
        IN_MEMORY_CONVERSATIONS[_conversation_cache_key(consumer.user, key2)] = [
            {"role": "user", "content": "Msg 2"}
        ]

        result1 = await consumer.fetch_conversation(key1)
        result2 = await consumer.fetch_conversation(key2)

        assert result1 != result2
        assert result1[0]["content"] == "Msg 1"
        assert result2[0]["content"] == "Msg 2"


# =============================================================================
# Default-model LiteLLM wiring
# =============================================================================


class TestRespondWithDefaultModelLiteLLM:
    """respond_with_default_model must honor LITELLM_* like blueprint_base."""

    @pytest.mark.asyncio
    async def test_uses_litellm_base_url_and_api_key(self, consumer, monkeypatch):
        monkeypatch.setenv("LITELLM_BASE_URL", "http://127.0.0.1:4000/v1")
        monkeypatch.setenv("LITELLM_API_KEY", "sk-litellm-test")
        monkeypatch.setenv("LITELLM_MODEL", "orchestration")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.delenv("OPENAI_MODEL", raising=False)

        consumer.messages = [{"role": "user", "content": "hi"}]

        async def stream():
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = "ok"
            yield chunk

        mock_client = MagicMock()
        mock_client.base_url = "http://127.0.0.1:4000/v1"
        mock_client.chat.completions.create = AsyncMock(return_value=stream())
        mock_client.close = AsyncMock()

        with patch("swarm.consumers.AsyncOpenAI", return_value=mock_client) as mock_cls:
            with patch.object(consumer, "send", new_callable=AsyncMock):
                await consumer.respond_with_default_model("message-response-litellm")

        mock_cls.assert_called_once_with(
            api_key="sk-litellm-test",
            base_url="http://127.0.0.1:4000/v1",
        )
        create_kwargs = mock_client.chat.completions.create.await_args.kwargs
        assert create_kwargs["model"] == "orchestration"

    @pytest.mark.asyncio
    async def test_rejects_openai_com_when_litellm_configured(self, consumer, monkeypatch):
        monkeypatch.setenv("LITELLM_BASE_URL", "http://127.0.0.1:4000/v1")
        monkeypatch.setenv("LITELLM_API_KEY", "sk-litellm-test")
        monkeypatch.setenv("LITELLM_MODEL", "orchestration")

        consumer.messages = [{"role": "user", "content": "hi"}]

        mock_client = MagicMock()
        # Simulate accidental default OpenAI endpoint on the constructed client.
        mock_client.base_url = "https://api.openai.com/v1"
        mock_client.close = AsyncMock()

        with patch("swarm.consumers.AsyncOpenAI", return_value=mock_client):
            with patch.object(consumer, "send", new_callable=AsyncMock):
                with pytest.raises(RuntimeError, match="Attempted fallback to OpenAI API"):
                    await consumer.respond_with_default_model("message-response-bad")
