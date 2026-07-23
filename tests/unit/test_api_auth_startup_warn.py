"""Startup footgun: warn when serving with API auth off."""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest


@pytest.mark.django_db
def test_warns_when_serving_without_api_auth(settings, monkeypatch):
    from swarm import apps as apps_mod
    from swarm.apps import SwarmConfig

    settings.ENABLE_API_AUTH = False
    monkeypatch.setattr(sys, "argv", ["uvicorn", "swarm.asgi:application"])
    with patch.object(apps_mod.logger, "warning") as warn:
        SwarmConfig._warn_if_api_auth_disabled()
    warn.assert_called_once()
    assert "API authentication is OFF" in warn.call_args[0][0]


@pytest.mark.django_db
def test_no_warn_when_api_auth_on(settings, monkeypatch):
    from swarm import apps as apps_mod
    from swarm.apps import SwarmConfig

    settings.ENABLE_API_AUTH = True
    monkeypatch.setattr(sys, "argv", ["uvicorn", "swarm.asgi:application"])
    with patch.object(apps_mod.logger, "warning") as warn:
        SwarmConfig._warn_if_api_auth_disabled()
    warn.assert_not_called()


def test_no_warn_when_not_serving(settings, monkeypatch):
    from swarm import apps as apps_mod
    from swarm.apps import SwarmConfig

    settings.ENABLE_API_AUTH = False
    monkeypatch.setattr(sys, "argv", ["pytest"])
    with patch.object(apps_mod.logger, "warning") as warn:
        SwarmConfig._warn_if_api_auth_disabled()
    warn.assert_not_called()
