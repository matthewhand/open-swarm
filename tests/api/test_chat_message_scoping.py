"""ChatMessageViewSet tenancy: session users only see their own conversations.

When ENABLE_API_AUTH is on:
- authenticated session users list only messages where conversation.student is them
- token-only / anonymous authenticated-via-token clients get an empty queryset
When auth is off, the open list behavior is preserved for local/dev.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from swarm.models import ChatConversation, ChatMessage
from swarm.views.message_views import ChatMessageViewSet

TOKEN = "chat-msg-scope-token-xyz"
User = get_user_model()


def _list_view():
    return ChatMessageViewSet.as_view({"get": "list"})


def _seed_messages():
    alice = User.objects.create_user(username="scope_alice", password="x")
    bob = User.objects.create_user(username="scope_bob", password="x")
    conv_alice = ChatConversation.objects.create(
        conversation_id="conv-alice-1", student=alice
    )
    conv_bob = ChatConversation.objects.create(
        conversation_id="conv-bob-1", student=bob
    )
    conv_legacy = ChatConversation.objects.create(
        conversation_id="conv-legacy-null", student=None
    )
    ChatMessage.objects.create(
        conversation=conv_alice, sender="user", content="alice-secret"
    )
    ChatMessage.objects.create(
        conversation=conv_bob, sender="user", content="bob-secret"
    )
    ChatMessage.objects.create(
        conversation=conv_legacy, sender="user", content="legacy-orphan"
    )
    return alice, bob


@pytest.mark.django_db
class TestChatMessageScoping:
    def test_session_user_sees_only_own_messages(self):
        alice, _bob = _seed_messages()
        factory = APIRequestFactory()
        request = factory.get("/v1/chat-messages/")
        force_authenticate(request, user=alice)
        with override_settings(ENABLE_API_AUTH=True, SWARM_API_KEY=TOKEN):
            response = _list_view()(request)
        assert response.status_code == 200
        contents = [row["content"] for row in response.data]
        assert "alice-secret" in contents
        assert "bob-secret" not in contents
        assert "legacy-orphan" not in contents

    def test_other_session_user_sees_only_theirs(self):
        _alice, bob = _seed_messages()
        factory = APIRequestFactory()
        request = factory.get("/v1/chat-messages/")
        force_authenticate(request, user=bob)
        with override_settings(ENABLE_API_AUTH=True, SWARM_API_KEY=TOKEN):
            response = _list_view()(request)
        assert response.status_code == 200
        contents = [row["content"] for row in response.data]
        assert contents == ["bob-secret"]

    def test_token_only_client_sees_empty_queryset(self):
        """Static token auth yields AnonymousUser + request.auth — no chat rows."""
        _seed_messages()
        factory = APIRequestFactory()
        request = factory.get(
            "/v1/chat-messages/",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
        # Run through StaticTokenAuthentication so request.auth is set and
        # request.user is AnonymousUser (session-less token client).
        from swarm.auth import StaticTokenAuthentication

        with override_settings(ENABLE_API_AUTH=True, SWARM_API_KEY=TOKEN):
            user_auth = StaticTokenAuthentication().authenticate(request)
            assert user_auth is not None
            request.user, request.auth = user_auth
            response = _list_view()(request)
        assert response.status_code == 200
        assert list(response.data) == []

    def test_unauthenticated_denied_when_auth_on(self):
        _seed_messages()
        factory = APIRequestFactory()
        request = factory.get("/v1/chat-messages/")
        with override_settings(ENABLE_API_AUTH=True, SWARM_API_KEY=TOKEN):
            response = _list_view()(request)
        assert response.status_code in (401, 403)

    def test_open_list_when_auth_off(self):
        _seed_messages()
        factory = APIRequestFactory()
        request = factory.get("/v1/chat-messages/")
        with override_settings(ENABLE_API_AUTH=False, SWARM_API_KEY=None):
            response = _list_view()(request)
        assert response.status_code == 200
        contents = {row["content"] for row in response.data}
        assert {"alice-secret", "bob-secret", "legacy-orphan"} <= contents

    def test_create_stamps_student_on_null_conversation(self):
        alice = User.objects.create_user(username="create_alice", password="x")
        conv = ChatConversation.objects.create(
            conversation_id="conv-stamp-me", student=None
        )
        factory = APIRequestFactory()
        request = factory.post(
            "/v1/chat-messages/",
            {"conversation": conv.conversation_id, "sender": "user", "content": "hi"},
            format="json",
        )
        force_authenticate(request, user=alice)
        view = ChatMessageViewSet.as_view({"post": "create"})
        with override_settings(ENABLE_API_AUTH=True, SWARM_API_KEY=TOKEN):
            response = view(request)
        assert response.status_code == 201, getattr(response, "data", response.content)
        conv.refresh_from_db()
        assert conv.student_id == alice.id
