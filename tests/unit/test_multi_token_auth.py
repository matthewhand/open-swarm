"""Multi-token API auth: multiple Bearer secrets → distinct ownership principals."""
from __future__ import annotations

import hashlib

import pytest
from django.test import override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from swarm.auth import StaticTokenAuthentication, request_principal
from swarm.utils import env_utils


TOKEN_A = "multi-token-alpha-secret"
TOKEN_B = "multi-token-beta-secret"
TOKEN_SINGLE = "single-token-gamma-secret"


def _token_principal(token: str) -> str:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]
    return f"token:{digest}"


# =============================================================================
# env_utils: get_api_auth_tokens merge + dedupe
# =============================================================================


class TestGetApiAuthTokens:
    def test_merges_single_and_multi(self, monkeypatch):
        monkeypatch.delenv("SWARM_ALLOW_NO_AUTH", raising=False)
        monkeypatch.setenv("API_AUTH_TOKEN", "primary")
        monkeypatch.setenv("SWARM_API_KEY", "legacy")
        monkeypatch.setenv("API_AUTH_TOKENS", "extra1,extra2")
        monkeypatch.delenv("SWARM_API_KEYS", raising=False)
        assert env_utils.get_api_auth_tokens() == [
            "primary",
            "legacy",
            "extra1",
            "extra2",
        ]

    def test_dedupes_overlap(self, monkeypatch):
        monkeypatch.delenv("SWARM_ALLOW_NO_AUTH", raising=False)
        monkeypatch.setenv("API_AUTH_TOKEN", "same")
        monkeypatch.setenv("SWARM_API_KEY", "same")
        monkeypatch.setenv("API_AUTH_TOKENS", "same,other")
        monkeypatch.delenv("SWARM_API_KEYS", raising=False)
        assert env_utils.get_api_auth_tokens() == ["same", "other"]

    def test_multi_only(self, monkeypatch):
        monkeypatch.delenv("SWARM_ALLOW_NO_AUTH", raising=False)
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("SWARM_API_KEY", raising=False)
        monkeypatch.setenv("SWARM_API_KEYS", "a,b")
        monkeypatch.delenv("API_AUTH_TOKENS", raising=False)
        assert env_utils.get_api_auth_tokens() == ["a", "b"]
        assert env_utils.get_api_auth_token() == "a"

    def test_allow_no_auth_returns_empty(self, monkeypatch):
        monkeypatch.setenv("SWARM_ALLOW_NO_AUTH", "true")
        monkeypatch.setenv("API_AUTH_TOKEN", "tok")
        monkeypatch.setenv("API_AUTH_TOKENS", "a,b")
        assert env_utils.get_api_auth_tokens() == []
        assert env_utils.get_api_auth_token() is None

    def test_empty_when_unset(self, monkeypatch):
        monkeypatch.delenv("SWARM_ALLOW_NO_AUTH", raising=False)
        for key in (
            "API_AUTH_TOKEN",
            "SWARM_API_KEY",
            "API_AUTH_TOKENS",
            "SWARM_API_KEYS",
        ):
            monkeypatch.delenv(key, raising=False)
        assert env_utils.get_api_auth_tokens() == []


# =============================================================================
# StaticTokenAuthentication multi-key
# =============================================================================


class TestStaticTokenMultiKey:
    def test_both_tokens_authenticate(self):
        factory = APIRequestFactory()
        auth = StaticTokenAuthentication()
        with override_settings(
            ENABLE_API_AUTH=True,
            SWARM_API_KEY=TOKEN_A,
            SWARM_API_KEYS=[TOKEN_A, TOKEN_B],
        ):
            for tok in (TOKEN_A, TOKEN_B):
                req = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {tok}")
                pair = auth.authenticate(req)
                assert pair is not None
                user, provided = pair
                assert provided == tok
                assert not user.is_authenticated  # AnonymousUser

    def test_invalid_token_fails(self):
        factory = APIRequestFactory()
        auth = StaticTokenAuthentication()
        with override_settings(
            ENABLE_API_AUTH=True,
            SWARM_API_KEY=TOKEN_A,
            SWARM_API_KEYS=[TOKEN_A, TOKEN_B],
        ):
            req = factory.get("/", HTTP_AUTHORIZATION="Bearer not-a-valid-key")
            with pytest.raises(AuthenticationFailed):
                auth.authenticate(req)

    def test_single_token_still_works(self):
        factory = APIRequestFactory()
        auth = StaticTokenAuthentication()
        with override_settings(
            ENABLE_API_AUTH=True,
            SWARM_API_KEY=TOKEN_SINGLE,
            SWARM_API_KEYS=[TOKEN_SINGLE],
        ):
            req = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {TOKEN_SINGLE}")
            pair = auth.authenticate(req)
            assert pair is not None
            assert pair[1] == TOKEN_SINGLE

    def test_fallback_to_swarm_api_key_when_keys_empty(self):
        """Backward compat: only SWARM_API_KEY set (no SWARM_API_KEYS list)."""
        factory = APIRequestFactory()
        auth = StaticTokenAuthentication()
        with override_settings(
            ENABLE_API_AUTH=True,
            SWARM_API_KEY=TOKEN_SINGLE,
            SWARM_API_KEYS=[],
        ):
            req = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {TOKEN_SINGLE}")
            pair = auth.authenticate(req)
            assert pair is not None
            assert pair[1] == TOKEN_SINGLE

    def test_x_api_key_header(self):
        factory = APIRequestFactory()
        auth = StaticTokenAuthentication()
        with override_settings(
            ENABLE_API_AUTH=True,
            SWARM_API_KEY=TOKEN_A,
            SWARM_API_KEYS=[TOKEN_A, TOKEN_B],
        ):
            req = factory.get("/", HTTP_X_API_KEY=TOKEN_B)
            pair = auth.authenticate(req)
            assert pair is not None
            assert pair[1] == TOKEN_B


# =============================================================================
# request_principal differs per presenting token
# =============================================================================


class TestRequestPrincipalMultiKey:
    def test_principals_differ_for_a_vs_b(self):
        factory = APIRequestFactory()
        auth = StaticTokenAuthentication()
        with override_settings(
            ENABLE_API_AUTH=True,
            SWARM_API_KEY=TOKEN_A,
            SWARM_API_KEYS=[TOKEN_A, TOKEN_B],
        ):
            principals = []
            for tok in (TOKEN_A, TOKEN_B):
                req = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {tok}")
                pair = auth.authenticate(req)
                assert pair is not None
                req.user, req.auth = pair
                p = request_principal(req)
                principals.append(p)
                assert p == _token_principal(tok)

            assert principals[0] != principals[1]
            assert principals[0].startswith("token:")
            assert principals[1].startswith("token:")

    def test_single_token_principal(self):
        factory = APIRequestFactory()
        auth = StaticTokenAuthentication()
        with override_settings(
            ENABLE_API_AUTH=True,
            SWARM_API_KEY=TOKEN_SINGLE,
            SWARM_API_KEYS=[TOKEN_SINGLE],
        ):
            req = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {TOKEN_SINGLE}")
            pair = auth.authenticate(req)
            req.user, req.auth = pair
            assert request_principal(req) == _token_principal(TOKEN_SINGLE)
