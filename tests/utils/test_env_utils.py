import os
from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured

from swarm.utils.env_utils import (
    get_csv_env,
    get_django_allowed_hosts,
    get_django_secret_key,
    get_swarm_config_path,
    get_swarm_log_level,
    is_django_debug,
    is_enable_wagtail,
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


@pytest.mark.parametrize(
    "value, expected",
    [
        ("true", True),
        ("1", True),
        ("t", True),
        ("false", False),
        ("0", False),
        ("", False),
    ],
)
def test_is_django_debug(value, expected):
    with patch.dict(os.environ, {"DJANGO_DEBUG": value}):
        assert is_django_debug() is expected


def test_is_django_debug_defaults_to_false_when_unset():
    with patch.dict(os.environ, {}, clear=True):
        assert is_django_debug() is False


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
def test_is_enable_wagtail(value, expected):
    with patch.dict(os.environ, {"ENABLE_WAGTAIL": value}):
        assert is_enable_wagtail() is expected


def test_is_enable_wagtail_defaults_to_false_when_unset():
    with patch.dict(os.environ, {}, clear=True):
        assert is_enable_wagtail() is False


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
