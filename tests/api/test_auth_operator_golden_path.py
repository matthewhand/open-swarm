"""Golden path under auth: create → own → list (Session Explorer bridge).

Operator story (docs/AUTH.md §1 + §4):

1. With ``ENABLE_API_AUTH`` and a configured API token, ``POST /v1/responses``
   (Bearer **or** Django session) stamps ``owner`` on the queued/stored record.
2. Session Explorer (``/sessions/``, ``/api/sessions/``) is an **operator
   bridge**: a logged-in Django user sees their ``user:…`` sessions **and**
   sessions owned by currently configured ``token:…`` principals (curl path).
3. REST ``GET /v1/responses/{id}`` stays strict same-principal IDOR — the
   bridge does **not** escalate API privileges.

This test exercises the real create path (background queue stamp) then asserts
Explorer + REST visibility stay coherent. It must FAIL if create→own→list
breaks (missing owner stamp, bridge regressions, or IDOR leaks).
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.test import AsyncClient, Client
from django.urls import reverse

from swarm.auth import token_principal
from swarm.core import responses_store

TOKEN = "golden-path-api-token-xyz"
FOREIGN_TOKEN = "golden-path-other-token-abc"


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_RESPONSES_DIR", str(tmp_path))
    # Hybrid/background queue is skipped when SWARM_TEST_MODE is set; ownership
    # is stamped on the initial queued save before the worker runs.
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    return tmp_path


@pytest.mark.django_db(transaction=True)
class TestAuthOperatorGoldenPath:
    """End-to-end create→own→list coherence under ENABLE_API_AUTH."""

    @pytest.fixture(autouse=True)
    def _auth_and_create_mocks(self, settings, monkeypatch, store):
        settings.ENABLE_API_AUTH = True
        settings.SWARM_API_KEY = TOKEN
        settings.SWARM_API_KEYS = [TOKEN]
        monkeypatch.setattr(
            "swarm.views.responses_views.validate_model_access", lambda *a, **k: True
        )
        monkeypatch.setattr(
            "swarm.views.responses_views._spawn_worker", lambda *a, **k: None
        )
        mock_bp = MagicMock()
        monkeypatch.setattr(
            "swarm.views.responses_views.get_blueprint_instance",
            AsyncMock(return_value=mock_bp),
        )

    async def _create_background(self, client: AsyncClient, *, bearer: str | None = None):
        # AsyncClient (ASGI) wants real header names via ``headers=``; passing
        # HTTP_AUTHORIZATION as **extra becomes HTTP_HTTP_AUTHORIZATION.
        kwargs: dict = {
            "data": json.dumps({
                "model": "chatbot",
                "input": "golden-path ping",
                "background": True,
            }),
            "content_type": "application/json",
            "SERVER_NAME": "localhost",
        }
        if bearer:
            kwargs["headers"] = {"Authorization": f"Bearer {bearer}"}
        return await client.post(reverse("responses"), **kwargs)

    @pytest.mark.asyncio
    async def test_create_own_list_session_and_token_bridge(self, store, settings):
        """Bearer create + session create → Explorer bridge + REST IDOR coherent."""
        User = get_user_model()
        alice = await sync_to_async(User.objects.create_user)(
            username="gp_alice", password="x"
        )
        bob = await sync_to_async(User.objects.create_user)(
            username="gp_bob", password="x"
        )

        # --- 1) Session user creates a response (owner = user:gp_alice) ---
        alice_api = AsyncClient()
        await sync_to_async(alice_api.force_login)(alice)
        created_user = await self._create_background(alice_api)
        assert created_user.status_code == 202, created_user.content
        user_body = json.loads(created_user.content)
        user_rid = user_body["id"]
        assert user_rid.startswith("resp_")
        user_rec = responses_store.load(user_rid)
        assert user_rec is not None
        assert user_rec.get("owner") == "user:gp_alice", (
            "session create must stamp owner=user:<username> or Explorer/REST break"
        )

        # --- 2) Bearer/curl creates a response (owner = token:<sha256-prefix>) ---
        token_api = AsyncClient()
        created_token = await self._create_background(token_api, bearer=TOKEN)
        assert created_token.status_code == 202, created_token.content
        token_body = json.loads(created_token.content)
        token_rid = token_body["id"]
        expected_token_owner = token_principal(TOKEN)
        token_rec = responses_store.load(token_rid)
        assert token_rec is not None
        assert token_rec.get("owner") == expected_token_owner, (
            "Bearer create must stamp owner=token:<prefix> for the operator bridge"
        )
        assert user_rid != token_rid

        # Seed a foreign-user row that must stay hidden from Alice/Bob explorer.
        responses_store.save({
            "id": "resp_gp_stranger",
            "object": "response",
            "owner": "user:stranger",
            "response": {
                "id": "resp_gp_stranger",
                "object": "response",
                "status": "completed",
                "model": "chatbot",
                "created_at": 99,
                "output_text": "stranger-secret",
                "progress": [],
            },
            "messages": [{"role": "user", "content": "hi"}],
        })

        # --- 3) Session Explorer operator bridge (Alice sees user + configured token) ---
        alice_web = Client()
        await sync_to_async(alice_web.force_login)(alice)
        feed = await sync_to_async(alice_web.get)(reverse("session-list-api"))
        assert feed.status_code == 200
        alice_ids = {s["id"] for s in json.loads(feed.content)["sessions"]}
        assert user_rid in alice_ids, "Alice must see her own session in Explorer"
        assert token_rid in alice_ids, (
            "Alice must see configured Bearer/token-owned sessions (operator bridge)"
        )
        assert "resp_gp_stranger" not in alice_ids

        page = await sync_to_async(alice_web.get)(reverse("session-explorer"))
        assert page.status_code == 200
        page_body = page.content.decode()
        assert user_rid in page_body and token_rid in page_body
        assert "stranger-secret" not in page_body

        # Detail pages resolve for both bridged owners.
        assert (
            await sync_to_async(alice_web.get)(
                reverse("session-detail", kwargs={"response_id": user_rid})
            )
        ).status_code == 200
        assert (
            await sync_to_async(alice_web.get)(
                reverse("session-detail", kwargs={"response_id": token_rid})
            )
        ).status_code == 200
        assert (
            await sync_to_async(alice_web.get)(
                reverse("session-detail", kwargs={"response_id": "resp_gp_stranger"})
            )
        ).status_code == 404

        # Bob (other Django user): sees token bridge, not Alice's user: session.
        bob_web = Client()
        await sync_to_async(bob_web.force_login)(bob)
        bob_feed = await sync_to_async(bob_web.get)(reverse("session-list-api"))
        assert bob_feed.status_code == 200
        bob_ids = {s["id"] for s in json.loads(bob_feed.content)["sessions"]}
        assert token_rid in bob_ids
        assert user_rid not in bob_ids
        assert "resp_gp_stranger" not in bob_ids

        # --- 4) REST IDOR stays strict (bridge ≠ API privilege) ---
        ok_own = await alice_api.get(f"/v1/responses/{user_rid}", SERVER_NAME="localhost")
        assert ok_own.status_code == 200

        denied_token = await alice_api.get(
            f"/v1/responses/{token_rid}", SERVER_NAME="localhost"
        )
        assert denied_token.status_code == 403, (
            "Session user must not REST-read token-owned responses (bridge is Explorer-only)"
        )

        token_get = await token_api.get(
            f"/v1/responses/{token_rid}",
            SERVER_NAME="localhost",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert token_get.status_code == 200

        token_denied_user = await token_api.get(
            f"/v1/responses/{user_rid}",
            SERVER_NAME="localhost",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert token_denied_user.status_code == 403

        bob_api = AsyncClient()
        await sync_to_async(bob_api.force_login)(bob)
        bob_denied_alice = await bob_api.get(
            f"/v1/responses/{user_rid}", SERVER_NAME="localhost"
        )
        assert bob_denied_alice.status_code == 403
        bob_denied_token = await bob_api.get(
            f"/v1/responses/{token_rid}", SERVER_NAME="localhost"
        )
        assert bob_denied_token.status_code == 403

        # Unrelated Bearer must not see either record via REST.
        settings.SWARM_API_KEYS = [TOKEN, FOREIGN_TOKEN]
        settings.SWARM_API_KEY = TOKEN
        foreign = AsyncClient()
        foreign_user = await foreign.get(
            f"/v1/responses/{user_rid}",
            SERVER_NAME="localhost",
            headers={"Authorization": f"Bearer {FOREIGN_TOKEN}"},
        )
        foreign_token = await foreign.get(
            f"/v1/responses/{token_rid}",
            SERVER_NAME="localhost",
            headers={"Authorization": f"Bearer {FOREIGN_TOKEN}"},
        )
        assert foreign_user.status_code == 403
        assert foreign_token.status_code == 403
