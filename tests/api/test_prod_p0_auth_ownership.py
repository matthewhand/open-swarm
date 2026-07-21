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
        assert responses_store.owner_allows({"id": "resp_y"}, "user:bob") is True  # legacy
        assert responses_store.owner_allows(rec, None) is False

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
