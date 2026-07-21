"""Production P0: discovery auth lock + response ownership (IDOR refuse).

Drives real permissioned views (ModelsListView / BlueprintsListView /
Responses detail/cancel) — not reimplemented stubs.
"""
from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from swarm.auth import StaticTokenAuthentication, request_principal
from swarm.core import responses_store
from swarm.views.api_views import BlueprintsListView, ModelsListView
from swarm.views.responses_views import ResponsesCancelView, ResponsesDetailView


TOKEN = "prod-p0-test-token-xyz"


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_RESPONSES_DIR", str(tmp_path))
    return tmp_path


@pytest.mark.django_db
class TestDiscoveryAuthLock:
    def test_models_open_when_api_auth_disabled(self):
        factory = APIRequestFactory()
        request = factory.get("/v1/models")
        view = ModelsListView.as_view()
        with override_settings(ENABLE_API_AUTH=False, SWARM_API_KEY=None):
            response = view(request)
        assert response.status_code == 200

    def test_models_requires_auth_when_enabled(self):
        factory = APIRequestFactory()
        request = factory.get("/v1/models")
        view = ModelsListView.as_view()
        with override_settings(ENABLE_API_AUTH=True, SWARM_API_KEY=TOKEN):
            response = view(request)
        # DRF permission denied → 403
        assert response.status_code in (401, 403)

    def test_models_ok_with_bearer_token(self):
        factory = APIRequestFactory()
        request = factory.get("/v1/models", HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
        # Run authentication so request.auth is set
        with override_settings(ENABLE_API_AUTH=True, SWARM_API_KEY=TOKEN):
            auth = StaticTokenAuthentication()
            user_auth = auth.authenticate(request)
            assert user_auth is not None
            request.user, request.auth = user_auth
            view = ModelsListView.as_view()
            response = view(request)
        assert response.status_code == 200
        assert "data" in response.data

    def test_blueprints_requires_auth_when_enabled(self):
        factory = APIRequestFactory()
        request = factory.get("/v1/blueprints")
        view = BlueprintsListView.as_view()
        with override_settings(ENABLE_API_AUTH=True, SWARM_API_KEY=TOKEN):
            response = view(request)
        assert response.status_code in (401, 403)

    def test_blueprints_ok_with_token(self):
        factory = APIRequestFactory()
        request = factory.get("/v1/blueprints", HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
        with override_settings(ENABLE_API_AUTH=True, SWARM_API_KEY=TOKEN):
            auth = StaticTokenAuthentication()
            user_auth = auth.authenticate(request)
            request.user, request.auth = user_auth
            response = BlueprintsListView.as_view()(request)
        assert response.status_code == 200


@pytest.mark.django_db
class TestResponseOwnership:
    def _save(self, rid: str, owner: str | None):
        responses_store.save({
            "id": rid,
            "object": "response",
            "owner": owner,
            "response": {
                "id": rid,
                "object": "response",
                "status": "completed",
                "output_text": "hello",
            },
            "messages": [{"role": "user", "content": "hi"}],
        })

    def test_owner_allows_helper(self, store):
        rec = {"id": "resp_x", "owner": "user:alice"}
        assert responses_store.owner_allows(rec, "user:alice") is True
        assert responses_store.owner_allows(rec, "user:bob") is False
        # Legacy unowned records fail closed (views skip check when auth off).
        assert responses_store.owner_allows({"id": "resp_y"}, "user:bob") is False
        assert responses_store.owner_allows({"id": "resp_y", "owner": None}, "user:bob") is False
        assert responses_store.owner_allows(rec, None) is False
        assert responses_store.owner_allows(None, "user:alice") is False

    def test_get_refuses_foreign_principal(self, store):
        User = get_user_model()
        alice = User.objects.create_user(username="alice_p0", password="x")
        bob = User.objects.create_user(username="bob_p0", password="x")
        self._save("resp_owned_alice", "user:alice_p0")

        from rest_framework.request import Request
        from rest_framework.exceptions import PermissionDenied
        from swarm.views.responses_views import _assert_owner_access

        factory = APIRequestFactory()
        req = factory.get("/v1/responses/resp_owned_alice")
        force_authenticate(req, user=bob)
        drf_req = Request(req)
        drf_req.user = bob
        drf_req.auth = None
        rec = responses_store.load("resp_owned_alice")
        with override_settings(ENABLE_API_AUTH=True, SWARM_API_KEY=TOKEN):
            assert request_principal(drf_req) == "user:bob_p0"
            with pytest.raises(PermissionDenied):
                _assert_owner_access(drf_req, rec)

        # Same principal OK
        force_authenticate(req, user=alice)
        drf_req.user = alice
        with override_settings(ENABLE_API_AUTH=True, SWARM_API_KEY=TOKEN):
            _assert_owner_access(drf_req, rec)  # no raise

    def test_cancel_refuses_foreign_owner(self, store):
        User = get_user_model()
        alice = User.objects.create_user(username="alice_c", password="x")
        bob = User.objects.create_user(username="bob_c", password="x")
        self._save("resp_cancel_alice", "user:alice_c")
        factory = APIRequestFactory()
        req = factory.post("/v1/responses/resp_cancel_alice/cancel")
        force_authenticate(req, user=bob)
        from rest_framework.request import Request
        from rest_framework.exceptions import PermissionDenied
        from swarm.views.responses_views import _assert_owner_access

        drf_req = Request(req)
        drf_req.user = bob
        rec = responses_store.load("resp_cancel_alice")
        with override_settings(ENABLE_API_AUTH=True, SWARM_API_KEY=TOKEN):
            with pytest.raises(PermissionDenied):
                _assert_owner_access(drf_req, rec)

    def test_request_principal_session_and_token(self):
        User = get_user_model()
        u = User.objects.create_user(username="prin_user", password="x")
        factory = APIRequestFactory()
        req = factory.get("/")
        force_authenticate(req, user=u)
        from rest_framework.request import Request

        drf = Request(req)
        drf.user = u
        drf.auth = None
        assert request_principal(drf) == "user:prin_user"

        req2 = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
        with override_settings(SWARM_API_KEY=TOKEN):
            pair = StaticTokenAuthentication().authenticate(req2)
            assert pair is not None
            req2.user, req2.auth = pair
            drf2 = Request(req2)
            drf2.user, drf2.auth = pair
            p = request_principal(drf2)
            assert p is not None and p.startswith("token:")


# --- Full HTTP (ASGI AsyncClient) ownership refusal when auth is on --------- #

@pytest.mark.django_db(transaction=True)
class TestResponseOwnershipHTTP:
    """GET / cancel / delete must refuse foreign + legacy-unowned when auth on."""

    def _save(self, rid: str, owner: str | None, *, status_str: str = "completed"):
        rec = {
            "id": rid,
            "object": "response",
            "response": {
                "id": rid,
                "object": "response",
                "status": status_str,
                "output_text": "hello",
                "output": [],
            },
            "messages": [{"role": "user", "content": "hi"}],
        }
        if owner is not None:
            rec["owner"] = owner
        # Explicitly omit owner key when None to model true legacy records.
        responses_store.save(rec)

    @pytest.fixture
    async def alice_client(self, db):
        from asgiref.sync import sync_to_async
        from django.contrib.auth import get_user_model
        from django.test import AsyncClient

        User = get_user_model()
        user, _ = await sync_to_async(User.objects.get_or_create)(username="http_alice")
        if not user.has_usable_password():
            await sync_to_async(user.set_password)("x")
            await sync_to_async(user.save)()
        client = AsyncClient()
        await sync_to_async(client.force_login)(user)
        return client

    @pytest.fixture
    async def bob_client(self, db):
        from asgiref.sync import sync_to_async
        from django.contrib.auth import get_user_model
        from django.test import AsyncClient

        User = get_user_model()
        user, _ = await sync_to_async(User.objects.get_or_create)(username="http_bob")
        if not user.has_usable_password():
            await sync_to_async(user.set_password)("x")
            await sync_to_async(user.save)()
        client = AsyncClient()
        await sync_to_async(client.force_login)(user)
        return client

    @pytest.mark.asyncio
    async def test_get_refuses_foreign_owner_http(self, store, alice_client, bob_client, settings):
        settings.ENABLE_API_AUTH = True
        settings.SWARM_API_KEY = TOKEN
        self._save("resp_http_alice", "user:http_alice")

        # Owner can read
        ok = await alice_client.get("/v1/responses/resp_http_alice", SERVER_NAME="localhost")
        assert ok.status_code == 200
        assert json.loads(ok.content)["id"] == "resp_http_alice"

        # Foreign principal denied
        denied = await bob_client.get("/v1/responses/resp_http_alice", SERVER_NAME="localhost")
        assert denied.status_code == 403

    @pytest.mark.asyncio
    async def test_get_refuses_legacy_unowned_when_auth_on(self, store, bob_client, settings):
        settings.ENABLE_API_AUTH = True
        settings.SWARM_API_KEY = TOKEN
        self._save("resp_http_legacy", None)  # no owner field

        denied = await bob_client.get("/v1/responses/resp_http_legacy", SERVER_NAME="localhost")
        assert denied.status_code == 403

    @pytest.mark.asyncio
    async def test_legacy_unowned_open_when_auth_off(self, store, bob_client, settings):
        settings.ENABLE_API_AUTH = False
        self._save("resp_http_legacy_open", None)

        ok = await bob_client.get("/v1/responses/resp_http_legacy_open", SERVER_NAME="localhost")
        assert ok.status_code == 200

    @pytest.mark.asyncio
    async def test_cancel_refuses_foreign_and_legacy_http(self, store, alice_client, bob_client, settings):
        settings.ENABLE_API_AUTH = True
        settings.SWARM_API_KEY = TOKEN
        self._save("resp_http_cancel_alice", "user:http_alice", status_str="in_progress")
        self._save("resp_http_cancel_legacy", None, status_str="in_progress")

        foreign = await bob_client.post(
            "/v1/responses/resp_http_cancel_alice/cancel", SERVER_NAME="localhost"
        )
        assert foreign.status_code == 403

        legacy = await bob_client.post(
            "/v1/responses/resp_http_cancel_legacy/cancel", SERVER_NAME="localhost"
        )
        assert legacy.status_code == 403

        # Owner can cancel
        ok = await alice_client.post(
            "/v1/responses/resp_http_cancel_alice/cancel", SERVER_NAME="localhost"
        )
        assert ok.status_code == 200
        assert json.loads(ok.content)["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_delete_refuses_foreign_and_legacy_http(self, store, alice_client, bob_client, settings):
        settings.ENABLE_API_AUTH = True
        settings.SWARM_API_KEY = TOKEN
        self._save("resp_http_del_alice", "user:http_alice")
        self._save("resp_http_del_legacy", None)

        foreign = await bob_client.delete(
            "/v1/responses/resp_http_del_alice", SERVER_NAME="localhost"
        )
        assert foreign.status_code == 403
        assert responses_store.load("resp_http_del_alice") is not None  # still there

        legacy = await bob_client.delete(
            "/v1/responses/resp_http_del_legacy", SERVER_NAME="localhost"
        )
        assert legacy.status_code == 403
        assert responses_store.load("resp_http_del_legacy") is not None

        ok = await alice_client.delete(
            "/v1/responses/resp_http_del_alice", SERVER_NAME="localhost"
        )
        assert ok.status_code == 200
        assert responses_store.load("resp_http_del_alice") is None

    def test_list_summaries_includes_owner(self, store):
        self._save("resp_sum_owned", "user:alice")
        self._save("resp_sum_legacy", None)
        rows = {r["id"]: r for r in responses_store.list_summaries()}
        assert rows["resp_sum_owned"]["owner"] == "user:alice"
        assert rows["resp_sum_legacy"].get("owner") is None
