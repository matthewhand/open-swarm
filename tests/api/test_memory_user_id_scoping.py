"""Regression: HTTP chat/responses must scope blueprint memory per principal.

Without ``user_id=request_principal(request)`` on ``blueprint.run(...)``, all
authenticated callers share the config/"default" memory namespace.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.test import AsyncClient
from django.urls import reverse
from rest_framework import status

from swarm.auth import token_principal
from swarm.permissions import HasValidTokenOrSession
from swarm.views.chat_views import ChatCompletionsView
from swarm.views.responses_views import ResponsesView


def _capturing_run(sink: list):
    async def run(*_args, **kwargs):
        sink.append(kwargs.get("user_id"))
        yield {"messages": [{"role": "assistant", "content": "ok"}], "final": True}

    return run


@pytest.fixture
def two_users(db):
    User = get_user_model()
    alice, _ = User.objects.get_or_create(username="mem_alice")
    if not alice.has_usable_password():
        alice.set_password("password")
        alice.save()
    bob, _ = User.objects.get_or_create(username="mem_bob")
    if not bob.has_usable_password():
        bob.set_password("password")
        bob.save()
    return alice, bob


@pytest.mark.django_db(transaction=True)
class TestMemoryUserIdScoping:
    @pytest.fixture(autouse=True)
    def _auth_settings(self, settings):
        settings.ENABLE_API_AUTH = True
        settings.SWARM_API_KEY = "mem-scope-key"
        settings.SWARM_API_KEYS = ["mem-scope-key", "mem-scope-key-b"]

    @pytest.mark.asyncio
    async def test_chat_completions_distinct_principals_get_distinct_user_ids(
        self, mocker, two_users, settings,
    ):
        alice, bob = two_users
        captured: list = []
        bp = MagicMock()
        bp.run = _capturing_run(captured)
        mocker.patch(
            "swarm.views.chat_views.get_blueprint_instance",
            new_callable=AsyncMock,
            return_value=bp,
        )
        mocker.patch("swarm.views.chat_views.validate_model_access", return_value=True)
        mocker.patch.object(ChatCompletionsView, "permission_classes", [HasValidTokenOrSession])

        url = reverse("chat_completions")
        data = {"model": "echocraft", "messages": [{"role": "user", "content": "hi"}], "stream": False}

        for user in (alice, bob):
            client = AsyncClient()
            await sync_to_async(client.force_login)(user)
            resp = await client.post(url, data=json.dumps(data), content_type="application/json")
            assert resp.status_code == status.HTTP_200_OK

        assert captured == ["user:mem_alice", "user:mem_bob"]
        assert captured[0] != captured[1]

    @pytest.mark.asyncio
    async def test_chat_completions_streaming_passes_principal_user_id(
        self, mocker, two_users, settings,
    ):
        alice, bob = two_users
        captured: list = []
        bp = MagicMock()
        bp.run = _capturing_run(captured)
        mocker.patch(
            "swarm.views.chat_views.get_blueprint_instance",
            new_callable=AsyncMock,
            return_value=bp,
        )
        mocker.patch("swarm.views.chat_views.validate_model_access", return_value=True)
        mocker.patch.object(ChatCompletionsView, "permission_classes", [HasValidTokenOrSession])

        url = reverse("chat_completions")
        data = {"model": "echocraft", "messages": [{"role": "user", "content": "hi"}], "stream": True}

        for user in (alice, bob):
            client = AsyncClient()
            await sync_to_async(client.force_login)(user)
            resp = await client.post(url, data=json.dumps(data), content_type="application/json")
            assert resp.status_code == status.HTTP_200_OK
            # Drain SSE body so the generator runs.
            _ = b"".join([chunk async for chunk in resp.streaming_content])

        assert captured == ["user:mem_alice", "user:mem_bob"]

    @pytest.mark.asyncio
    async def test_responses_distinct_token_principals_get_distinct_user_ids(
        self, mocker, settings,
    ):
        from django.contrib.auth.models import AnonymousUser

        token_a = "mem-scope-key"
        token_b = "mem-scope-key-b"
        captured: list = []
        bp = MagicMock()
        bp.run = _capturing_run(captured)
        mocker.patch(
            "swarm.views.responses_views.get_blueprint_instance",
            new_callable=AsyncMock,
            return_value=bp,
        )
        mocker.patch("swarm.views.responses_views.validate_model_access", return_value=True)
        mocker.patch.object(ResponsesView, "permission_classes", [HasValidTokenOrSession])
        mocker.patch("swarm.auth.CustomSessionAuthentication.authenticate", return_value=None)

        url = reverse("responses")
        data = {"model": "echocraft", "input": "remember this", "store": False}

        for token in (token_a, token_b):
            mocker.patch(
                "swarm.auth.StaticTokenAuthentication.authenticate",
                return_value=(AnonymousUser(), token),
            )
            client = AsyncClient()
            resp = await client.post(
                url,
                data=json.dumps(data),
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            assert resp.status_code == status.HTTP_200_OK, resp.content

        expected = [token_principal(token_a), token_principal(token_b)]
        assert captured == expected
        assert captured[0] != captured[1]

    @pytest.mark.asyncio
    async def test_responses_streaming_passes_principal_user_id(self, mocker, two_users, settings):
        alice, bob = two_users
        captured: list = []
        bp = MagicMock()
        bp.run = _capturing_run(captured)
        mocker.patch(
            "swarm.views.responses_views.get_blueprint_instance",
            new_callable=AsyncMock,
            return_value=bp,
        )
        mocker.patch("swarm.views.responses_views.validate_model_access", return_value=True)
        mocker.patch.object(ResponsesView, "permission_classes", [HasValidTokenOrSession])

        url = reverse("responses")
        data = {"model": "echocraft", "input": "stream me", "stream": True, "store": False}

        for user in (alice, bob):
            client = AsyncClient()
            await sync_to_async(client.force_login)(user)
            resp = await client.post(url, data=json.dumps(data), content_type="application/json")
            assert resp.status_code == status.HTTP_200_OK
            _ = b"".join([chunk async for chunk in resp.streaming_content])

        assert captured == ["user:mem_alice", "user:mem_bob"]

    @pytest.mark.asyncio
    async def test_consume_blueprint_forwards_user_id(self, mocker):
        from swarm.views.responses_views import _consume_blueprint

        captured: list = []

        class _BP:
            async def run(self, messages, stream=False, **kwargs):
                captured.append(kwargs.get("user_id"))
                yield {"messages": [{"role": "assistant", "content": "done"}], "final": True}

        answer, _ = await _consume_blueprint(_BP(), [], user_id="user:carol")
        assert answer == "done"
        assert captured == ["user:carol"]
