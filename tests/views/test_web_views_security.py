"""Open-redirect and login redirect safety for custom_login."""

from unittest.mock import MagicMock, patch

import pytest
from django.http import QueryDict
from django.test import RequestFactory

from swarm.views.web_views import (
    _DEFAULT_POST_LOGIN_REDIRECT,
    _safe_post_login_redirect,
    custom_login,
)


@pytest.mark.django_db
class TestCustomLoginSecurity:
    def _authed_post(self, next_url: str):
        factory = RequestFactory()
        # Set ``next`` via QueryDict so backslashes/control chars are not
        # mangled by URL parsing (mirrors a raw query value after decode).
        request = factory.post("/accounts/login/", {"username": "test", "password": "pass"})
        q = QueryDict(mutable=True)
        q["next"] = next_url
        request.GET = q
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        with patch("swarm.views.web_views.authenticate", return_value=mock_user), patch(
            "swarm.views.web_views.login"
        ):
            return custom_login(request)

    def test_custom_login_open_redirect_rejected(self):
        response = self._authed_post("http://malicious.com")
        assert response.status_code == 302
        assert response.url == _DEFAULT_POST_LOGIN_REDIRECT

    def test_custom_login_safe_redirect_allowed(self):
        safe_url = "/internal-path/"
        response = self._authed_post(safe_url)
        assert response.status_code == 302
        assert response.url == safe_url

    @pytest.mark.parametrize(
        "malicious_url",
        [
            "http://evil.com",
            "https://evil.com",
            "//evil.com",
            "//evil.com/path",
            "///evil.com",
            "////evil.com",
            "/\\evil.com",
            "\\\\evil.com",
            "\\evil.com",
            "/\\/evil.com",
            "http:\\\\evil.com",
            "//testserver@evil.com",
            "http://testserver@evil.com",
            "http://evil.com?testserver",
            "javascript:alert(1)",
            "data:text/html,hi",
            "ftp://testserver/",
            "//",
            "chatbot/",  # bare relative — not a rooted path
            "http://testserver/ok",  # absolute even to same host
            "//testserver/ok",  # scheme-relative same host
            "\n//evil.com",
            "/\tevil",
        ],
    )
    def test_custom_login_rejects_open_redirect_vectors(self, malicious_url):
        response = self._authed_post(malicious_url)
        assert response.status_code == 302
        assert response.url == _DEFAULT_POST_LOGIN_REDIRECT

    @pytest.mark.parametrize(
        "safe_url",
        [
            "/chatbot/",
            "/internal-path/",
            "/settings/?tab=auth",
            "/blueprint-library/",
            "/teams/",
        ],
    )
    def test_custom_login_allows_rooted_same_origin_paths(self, safe_url):
        response = self._authed_post(safe_url)
        assert response.status_code == 302
        assert response.url == safe_url


class TestSafePostLoginRedirectHelper:
    def test_fallback_on_none_or_blank(self):
        request = RequestFactory().get("/")
        assert _safe_post_login_redirect(request, None) == _DEFAULT_POST_LOGIN_REDIRECT
        assert _safe_post_login_redirect(request, "") == _DEFAULT_POST_LOGIN_REDIRECT
        assert _safe_post_login_redirect(request, "   ") == _DEFAULT_POST_LOGIN_REDIRECT

    def test_strips_whitespace_on_safe_path(self):
        request = RequestFactory().get("/")
        assert _safe_post_login_redirect(request, "  /chatbot/  ") == "/chatbot/"
