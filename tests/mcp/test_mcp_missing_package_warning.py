"""Guard: ENABLE_MCP_SERVER without the package logs a warning, not silence.

The '/mcp/' mount in swarm.urls imports 'django_mcp_server.urls', which no
installable package provides (the PyPI 'django-mcp-server' distribution exposes
'mcp_server' instead — see docs/mcp_server_mode.md). When the import fails the
except branch must emit a clear warning naming the missing module.
"""

import importlib
import logging
import sys

import pytest


@pytest.mark.django_db
def test_missing_mcp_package_logs_warning(monkeypatch, caplog, client):
    monkeypatch.setenv("ENABLE_MCP_SERVER", "true")

    # Ensure no stub from other tests masks the missing package.
    monkeypatch.delitem(sys.modules, "django_mcp_server.urls", raising=False)
    monkeypatch.delitem(sys.modules, "django_mcp_server", raising=False)

    # settings.LOGGING sets propagate=False on the 'swarm' logger; let records
    # reach the root handler so caplog can capture them.
    monkeypatch.setattr(logging.getLogger("swarm"), "propagate", True)

    from django.urls import clear_url_caches

    clear_url_caches()
    try:
        with caplog.at_level(logging.WARNING, logger="swarm.urls"):
            urls_mod = importlib.import_module("swarm.urls")
            importlib.reload(urls_mod)

        messages = [rec.getMessage() for rec in caplog.records]
        assert any("django_mcp_server" in msg for msg in messages), messages
        assert any("ENABLE_MCP_SERVER" in msg for msg in messages), messages

        # The mount must not exist (SPA fallback excludes mcp/, so plain 404).
        resp = client.get("/mcp/health/")
        assert resp.status_code == 404
    finally:
        # Restore default URLconf state for subsequent tests.
        monkeypatch.delenv("ENABLE_MCP_SERVER", raising=False)
        clear_url_caches()
        importlib.reload(importlib.import_module("swarm.urls"))
        clear_url_caches()
