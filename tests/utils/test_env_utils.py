import os
from unittest.mock import patch

import pytest

from swarm.utils.env_utils import (
    get_csv_env,
    get_django_allowed_hosts,
    get_django_secret_key,
    get_swarm_config_path,
    get_swarm_log_level,
    is_django_debug,
    is_truthy,
)


def test_get_django_secret_key():
    with patch.dict(os.environ, {"DJANGO_SECRET_KEY": "test-key"}):
        assert get_django_secret_key() == "test-key"
    with patch.dict(os.environ, {}, clear=True):
        assert get_django_secret_key() == "django-insecure-fallback-key-for-dev"


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


def test_get_django_allowed_hosts():
    with patch.dict(os.environ, {"DJANGO_ALLOWED_HOSTS": "example.com,test.com"}):
        assert get_django_allowed_hosts() == ["example.com", "test.com"]
    with patch.dict(os.environ, {}, clear=True):
        assert get_django_allowed_hosts() == ["localhost", "127.0.0.1"]


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
