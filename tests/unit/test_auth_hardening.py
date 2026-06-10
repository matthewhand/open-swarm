"""
Tests for auth-bypass hardening.

Covers:
- API_AUTH_TOKEN fallback and production enforcement (env_utils + settings boot)
- ALLOW_TESTUSER_AUTOLOGIN gating (default off, debug-only, refusal outside debug)
- No hardcoded 'testpass' password anywhere (per-process random / env override)
- custom_login testuser auto-login guard
- django_chat default-user debug guard
- runserver: auth-on default, --disable-auth dev-only refusal
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.management.base import CommandError
from django.test import RequestFactory

from swarm.utils import env_utils

REPO_ROOT = Path(__file__).resolve().parents[2]


# =============================================================================
# env_utils helpers
# =============================================================================

class TestGetApiAuthToken:
    def test_returns_api_auth_token(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "tok-a")
        monkeypatch.setenv("SWARM_API_KEY", "tok-b")
        assert env_utils.get_api_auth_token() == "tok-a"

    def test_falls_back_to_swarm_api_key(self, monkeypatch):
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        monkeypatch.setenv("SWARM_API_KEY", "tok-b")
        assert env_utils.get_api_auth_token() == "tok-b"

    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("SWARM_API_KEY", raising=False)
        assert env_utils.get_api_auth_token() is None


class TestGetEnforcedApiAuthToken:
    def test_returns_token_when_set(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "tok-a")
        monkeypatch.setenv("DJANGO_DEBUG", "false")
        assert env_utils.get_enforced_api_auth_token() == "tok-a"

    def test_debug_mode_allows_missing_token_with_warning(self, monkeypatch):
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("SWARM_API_KEY", raising=False)
        monkeypatch.setenv("DJANGO_DEBUG", "true")
        monkeypatch.setattr(env_utils, "_api_auth_disabled_warning_emitted", False)
        with patch.object(env_utils._logger, "warning") as mock_warning:
            assert env_utils.get_enforced_api_auth_token() is None
        assert mock_warning.call_count == 1
        assert "API authentication is DISABLED" in mock_warning.call_args[0][0]

    def test_debug_warning_only_emitted_once(self, monkeypatch):
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("SWARM_API_KEY", raising=False)
        monkeypatch.setenv("DJANGO_DEBUG", "true")
        monkeypatch.setattr(env_utils, "_api_auth_disabled_warning_emitted", False)
        with patch.object(env_utils._logger, "warning") as mock_warning:
            env_utils.get_enforced_api_auth_token()
            env_utils.get_enforced_api_auth_token()
        assert mock_warning.call_count == 1

    def test_production_refuses_without_token(self, monkeypatch):
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("SWARM_API_KEY", raising=False)
        monkeypatch.setenv("DJANGO_DEBUG", "false")
        with pytest.raises(ImproperlyConfigured, match="API_AUTH_TOKEN"):
            env_utils.get_enforced_api_auth_token()


class TestTestuserAutologinFlag:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("ALLOW_TESTUSER_AUTOLOGIN", raising=False)
        monkeypatch.setenv("DJANGO_DEBUG", "true")
        assert env_utils.is_testuser_autologin_allowed() is False

    def test_enabled_in_debug(self, monkeypatch):
        monkeypatch.setenv("ALLOW_TESTUSER_AUTOLOGIN", "true")
        monkeypatch.setenv("DJANGO_DEBUG", "true")
        assert env_utils.is_testuser_autologin_allowed() is True

    def test_refused_outside_debug(self, monkeypatch):
        monkeypatch.setenv("ALLOW_TESTUSER_AUTOLOGIN", "true")
        monkeypatch.setenv("DJANGO_DEBUG", "false")
        with pytest.raises(ImproperlyConfigured, match="ALLOW_TESTUSER_AUTOLOGIN"):
            env_utils.is_testuser_autologin_allowed()

    def test_disabled_flag_outside_debug_is_fine(self, monkeypatch):
        monkeypatch.delenv("ALLOW_TESTUSER_AUTOLOGIN", raising=False)
        monkeypatch.setenv("DJANGO_DEBUG", "false")
        assert env_utils.is_testuser_autologin_allowed() is False


class TestTestuserPassword:
    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("TESTUSER_PASSWORD", "from-env-secret")
        assert env_utils.get_testuser_password() == "from-env-secret"

    def test_generated_password_is_random_and_stable(self, monkeypatch):
        monkeypatch.delenv("TESTUSER_PASSWORD", raising=False)
        monkeypatch.setattr(env_utils, "_generated_testuser_password", None)
        pw1 = env_utils.get_testuser_password()
        pw2 = env_utils.get_testuser_password()
        assert pw1 == pw2  # stable within a process
        assert pw1 != "testpass"  # never the old hardcoded value
        assert len(pw1) >= 32

    def test_no_hardcoded_testpass_in_source(self):
        """The hardcoded 'testpass' password must not reappear in src/."""
        hits = []
        for py_file in (REPO_ROOT / "src").rglob("*.py"):
            if '"testpass"' in py_file.read_text(encoding="utf-8", errors="replace"):
                hits.append(str(py_file))
        assert hits == [], f"hardcoded 'testpass' found in: {hits}"


# =============================================================================
# settings.py boot enforcement (subprocess: clean import, no pytest guard)
# =============================================================================

def _settings_import_env(**overrides):
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        # Shield from any values in a developer's .env (load_dotenv does not
        # override variables that are already present in the environment).
        "API_AUTH_TOKEN": "",
        "SWARM_API_KEY": "",
        "DJANGO_SECRET_KEY": "test-secret-key-for-subprocess",
        "DJANGO_ALLOWED_HOSTS": "example.com",
        "DJANGO_DEBUG": "false",
    }
    env.update(overrides)
    return env


@pytest.mark.timeout(60)
def test_settings_production_boot_refuses_without_api_token():
    result = subprocess.run(
        [sys.executable, "-c", "import swarm.settings"],
        env=_settings_import_env(),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=50,
    )
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "API_AUTH_TOKEN" in result.stderr


@pytest.mark.timeout(60)
def test_settings_production_boot_succeeds_with_api_token():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import swarm.settings as s; print('AUTH', s.ENABLE_API_AUTH, s.SWARM_API_KEY)",
        ],
        env=_settings_import_env(API_AUTH_TOKEN="prod-token-123"),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=50,
    )
    assert result.returncode == 0, result.stderr
    assert "AUTH True prod-token-123" in result.stdout


# =============================================================================
# custom_login testuser auto-login guard
# =============================================================================

def _login_request(rf: RequestFactory):
    from django.contrib.sessions.middleware import SessionMiddleware
    request = rf.post("/accounts/login/", {"username": "nobody", "password": "wrong"})
    SessionMiddleware(lambda _request: None).process_request(request)
    request.session.save()
    return request


@pytest.mark.django_db
class TestCustomLoginAutologinGuard:
    def test_no_autologin_by_default(self, monkeypatch):
        """Failed login must NOT fall back to testuser when the flag is unset."""
        monkeypatch.delenv("ALLOW_TESTUSER_AUTOLOGIN", raising=False)
        from django.contrib.auth.models import User
        from django.http import HttpResponse

        from swarm.views.web_views import custom_login
        users_before = User.objects.count()
        with patch("swarm.views.web_views.render", return_value=HttpResponse(status=200)) as mock_render:
            response = custom_login(_login_request(RequestFactory()))
        assert response.status_code == 200  # error page, not a redirect
        assert mock_render.called
        assert User.objects.count() == users_before  # no user auto-created

    def test_autologin_when_flag_and_debug(self, monkeypatch):
        monkeypatch.setenv("ALLOW_TESTUSER_AUTOLOGIN", "true")
        monkeypatch.setenv("DJANGO_DEBUG", "true")
        monkeypatch.delenv("TESTUSER_PASSWORD", raising=False)
        from django.contrib.auth.models import User

        from swarm.views.web_views import custom_login
        response = custom_login(_login_request(RequestFactory()))
        assert response.status_code == 302
        user = User.objects.get(username="testuser")
        # The old hardcoded password must not work.
        assert not user.check_password("testpass")

    def test_autologin_refused_outside_debug(self, monkeypatch):
        monkeypatch.setenv("ALLOW_TESTUSER_AUTOLOGIN", "true")
        monkeypatch.setenv("DJANGO_DEBUG", "false")
        from django.contrib.auth.models import User

        from swarm.views.web_views import custom_login
        users_before = User.objects.count()
        with pytest.raises(ImproperlyConfigured):
            custom_login(_login_request(RequestFactory()))
        assert User.objects.count() == users_before  # no user auto-created


# =============================================================================
# django_chat default-user debug guard
# =============================================================================

@pytest.mark.django_db
class TestDjangoChatDefaultUserGuard:
    def test_refused_outside_debug(self, monkeypatch):
        monkeypatch.setenv("DJANGO_DEBUG", "false")
        from swarm.blueprints.django_chat.views import get_or_create_default_user
        with pytest.raises(PermissionDenied):
            get_or_create_default_user()

    def test_created_in_debug_without_hardcoded_password(self, monkeypatch):
        monkeypatch.setenv("DJANGO_DEBUG", "true")
        monkeypatch.delenv("TESTUSER_PASSWORD", raising=False)
        from django.contrib.auth.models import User

        from swarm.blueprints.django_chat.views import get_or_create_default_user
        user = get_or_create_default_user()
        assert user.username == "testuser"
        assert not User.objects.get(username="testuser").check_password("testpass")


# =============================================================================
# runserver management command: auth-on default, --disable-auth dev-only
# =============================================================================

@pytest.fixture
def restore_auth_settings():
    from django.conf import settings
    orig_enable = getattr(settings, "ENABLE_API_AUTH", None)
    orig_key = getattr(settings, "SWARM_API_KEY", None)
    yield
    settings.ENABLE_API_AUTH = orig_enable
    settings.SWARM_API_KEY = orig_key


@pytest.mark.usefixtures("restore_auth_settings")
class TestRunserverCommand:
    def _handle(self, **options):
        from django.core.management.commands.runserver import (
            Command as DjangoRunserver,
        )

        from swarm.management.commands.runserver import Command
        defaults = {"enable_auth": False, "disable_auth": False}
        defaults.update(options)
        with patch.object(DjangoRunserver, "handle", return_value=None) as mock_super:
            Command().handle(**defaults)
        return mock_super

    def test_disable_auth_refused_outside_debug(self, monkeypatch):
        monkeypatch.setenv("DJANGO_DEBUG", "false")
        with pytest.raises(CommandError, match="disable-auth"):
            self._handle(disable_auth=True)

    def test_disable_auth_allowed_in_debug(self, monkeypatch):
        from django.conf import settings
        monkeypatch.setenv("DJANGO_DEBUG", "true")
        mock_super = self._handle(disable_auth=True)
        assert mock_super.called
        assert settings.ENABLE_API_AUTH is False
        assert settings.SWARM_API_KEY is None

    def test_auth_enabled_by_default_with_token(self, monkeypatch):
        from django.conf import settings
        monkeypatch.setenv("DJANGO_DEBUG", "true")
        monkeypatch.setenv("API_AUTH_TOKEN", "cmd-token")
        mock_super = self._handle()
        assert mock_super.called
        assert settings.ENABLE_API_AUTH is True
        assert settings.SWARM_API_KEY == "cmd-token"

    def test_auth_inactive_without_token_in_debug(self, monkeypatch):
        from django.conf import settings
        monkeypatch.setenv("DJANGO_DEBUG", "true")
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("SWARM_API_KEY", raising=False)
        mock_super = self._handle()
        assert mock_super.called
        assert settings.ENABLE_API_AUTH is False

    def test_enable_auth_flag_is_deprecated_noop(self, monkeypatch):
        from django.conf import settings
        monkeypatch.setenv("DJANGO_DEBUG", "true")
        monkeypatch.setenv("API_AUTH_TOKEN", "cmd-token")
        mock_super = self._handle(enable_auth=True)
        assert mock_super.called
        assert settings.ENABLE_API_AUTH is True


# =============================================================================
# CSRF protection: state-mutating endpoints must not be csrf_exempt
# =============================================================================

class TestCsrfProtectionRestored:
    def test_team_admin_not_csrf_exempt(self):
        from swarm.views.web_views import team_admin
        assert not getattr(team_admin, "csrf_exempt", False)

    def test_settings_views_not_csrf_exempt(self):
        from swarm.views.settings_views import (
            environment_variables,
            settings_api,
            settings_dashboard,
        )
        for view in (settings_dashboard, settings_api, environment_variables):
            assert not getattr(view, "csrf_exempt", False), view.__name__

    def test_teams_admin_template_has_csrf_tokens(self):
        template = (
            REPO_ROOT / "src" / "swarm" / "templates" / "teams_admin.html"
        ).read_text(encoding="utf-8")
        assert template.count("{% csrf_token %}") >= template.count("<form")
