import os
from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured

from swarm.utils.env_utils import (
    build_mcp_stdio_env,
    get_csv_env,
    get_django_allowed_hosts,
    get_django_csrf_trusted_origins,
    get_django_secret_key,
    get_swarm_config_path,
    get_swarm_log_level,
    is_truthy,
)


def test_get_django_secret_key():
    with patch.dict(os.environ, {"DJANGO_SECRET_KEY": "test-key"}):
        assert get_django_secret_key() == "test-key"
    # Dev-only fallback requires DJANGO_DEBUG to be explicitly enabled.
    with patch.dict(os.environ, {"DJANGO_DEBUG": "true"}, clear=True):
        assert get_django_secret_key() == "django-insecure-fallback-key-for-dev"


def test_get_django_secret_key_required_in_production():
    # DJANGO_DEBUG unset -> production mode -> secret key is mandatory.
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
            get_django_secret_key()
    with patch.dict(os.environ, {"DJANGO_DEBUG": "false"}, clear=True):
        with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
            get_django_secret_key()



def test_get_django_allowed_hosts():
    with patch.dict(os.environ, {"DJANGO_ALLOWED_HOSTS": "example.com,test.com"}):
        assert get_django_allowed_hosts() == ["example.com", "test.com"]
    # Whitespace and empty entries are stripped.
    with patch.dict(os.environ, {"DJANGO_ALLOWED_HOSTS": " example.com , test.com ,"}):
        assert get_django_allowed_hosts() == ["example.com", "test.com"]
    # Localhost-only default applies in development only.
    with patch.dict(os.environ, {"DJANGO_DEBUG": "true"}, clear=True):
        assert get_django_allowed_hosts() == ["localhost", "127.0.0.1"]


def test_get_django_allowed_hosts_required_in_production():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ImproperlyConfigured, match="DJANGO_ALLOWED_HOSTS"):
            get_django_allowed_hosts()
    with patch.dict(os.environ, {"DJANGO_DEBUG": "false", "DJANGO_ALLOWED_HOSTS": ""}, clear=True):
        with pytest.raises(ImproperlyConfigured, match="DJANGO_ALLOWED_HOSTS"):
            get_django_allowed_hosts()


def test_get_swarm_config_path():
    with patch.dict(os.environ, {"SWARM_CONFIG_PATH": "/test/config.json"}):
        assert get_swarm_config_path() == "/test/config.json"


def test_get_swarm_log_level():
    with patch.dict(os.environ, {"SWARM_LOG_LEVEL": "INFO"}):
        assert get_swarm_log_level() == "INFO"
    with patch.dict(os.environ, {}, clear=True):
        assert get_swarm_log_level() == "DEBUG"


@pytest.mark.parametrize(
    "value, expected",
    [
        ("true", True),
        ("1", True),
        ("t", True),
        ("yes", True),
        ("y", True),
        ("false", False),
        ("0", False),
        ("", False),
    ],
)
def test_is_truthy(value, expected):
    assert is_truthy(value) is expected


def test_get_csv_env():
    with patch.dict(os.environ, {"MY_CSV_VAR": "a,b,c"}):
        assert get_csv_env("MY_CSV_VAR") == ["a", "b", "c"]
    with patch.dict(os.environ, {}, clear=True):
        assert get_csv_env("MY_CSV_VAR", "x,y") == ["x", "y"]
    with patch.dict(os.environ, {}, clear=True):
        assert get_csv_env("MY_CSV_VAR") == []


def test_get_csv_env_strips_whitespace_and_drops_empties():
    # A CSV env list should not yield padded or empty entries (a stray trailing
    # comma or " a , b " must not produce "" or " b ").
    with patch.dict(os.environ, {"MY_CSV_VAR": " a , b ,,c, "}):
        assert get_csv_env("MY_CSV_VAR") == ["a", "b", "c"]


def test_get_django_csrf_trusted_origins():
    with patch.dict(os.environ, {"DJANGO_CSRF_TRUSTED_ORIGINS": "https://a.com, https://b.com ,"}):
        assert get_django_csrf_trusted_origins() == ["https://a.com", "https://b.com"]
    # Default applies when unset.
    with patch.dict(os.environ, {}, clear=True):
        assert get_django_csrf_trusted_origins() == [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]


def test_build_mcp_stdio_env_does_not_leak_parent_secrets():
    """MCP stdio children must not inherit ambient API keys/tokens."""
    parent = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/home/test",
        "OPENAI_API_KEY": "sk-leak-me",
        "GITHUB_TOKEN": "ghp_leak",
        "SECRET_UNRELATED": "nope",
    }
    with patch.dict(os.environ, parent, clear=True):
        env = build_mcp_stdio_env({"MIRO-OAUTH-KEY": "miro-ok"})
    assert env["PATH"] == "/usr/bin:/bin"
    assert env["HOME"] == "/home/test"
    assert env["MIRO-OAUTH-KEY"] == "miro-ok"
    assert "OPENAI_API_KEY" not in env
    assert "GITHUB_TOKEN" not in env
    assert "SECRET_UNRELATED" not in env


def test_build_mcp_stdio_env_empty_server_env_is_essentials_only():
    with patch.dict(os.environ, {"PATH": "/bin", "OPENAI_API_KEY": "sk-x"}, clear=True):
        env = build_mcp_stdio_env(None)
    assert env == {"PATH": "/bin"}
    assert "OPENAI_API_KEY" not in env
