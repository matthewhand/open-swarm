"""MCPIntegrationConfig.ready() must log failures, not swallow them silently."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from django.apps import apps


@pytest.mark.django_db
def test_ready_logs_when_registration_fails(monkeypatch, caplog):
    from django.conf import settings as dj_settings

    monkeypatch.setattr(dj_settings, "ENABLE_MCP_SERVER", True, raising=False)
    # settings.LOGGING sets propagate=False on the 'swarm' logger; let records
    # reach the root handler so caplog can capture them.
    monkeypatch.setattr(logging.getLogger("swarm"), "propagate", True)

    cfg = apps.get_app_config("mcp")
    with patch(
        "swarm.mcp.integration.register_blueprints_with_mcp",
        side_effect=RuntimeError("boom"),
    ):
        with caplog.at_level(logging.ERROR, logger="swarm.mcp.apps"):
            cfg.ready()

    messages = [rec.getMessage() for rec in caplog.records]
    assert any("MCP blueprint registration failed" in msg for msg in messages), messages
    assert any(rec.exc_info for rec in caplog.records), "expected exception info logged"

@pytest.mark.django_db
def test_ready_registers_when_enabled(monkeypatch):
    from django.conf import settings as dj_settings

    monkeypatch.setattr(dj_settings, "ENABLE_MCP_SERVER", True, raising=False)
    calls = []

    cfg = apps.get_app_config("mcp")
    with patch(
        "swarm.mcp.integration.register_blueprints_with_mcp",
        side_effect=lambda: calls.append(1) or 0,
    ):
        cfg.ready()

    assert calls == [1]
