"""Guard: ENABLE_MCP_SERVER without the package logs a warning, not silence.

The '/mcp/' mount in swarm.urls imports 'mcp_server.urls' (provided by the
'django-mcp-server' distribution, installed via `pip install open-swarm[mcp]`).
When that import fails the except branch must emit a clear warning naming the
missing module. We force the import to fail hermetically (whether or not the
package happens to be installed in the dev env) by masking it in sys.modules.
"""

import importlib
import logging
import sys

import pytest


@pytest.mark.django_db
def test_missing_mcp_package_logs_warning(monkeypatch, caplog, client):
    monkeypatch.setenv("ENABLE_MCP_SERVER", "true")

    # Force the '/mcp/' mount import to fail regardless of whether the real
    # package is installed: a None entry in sys.modules makes `import` raise.
    monkeypatch.setitem(sys.modules, "mcp_server.urls", None)

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
        assert any("mcp_server" in msg for msg in messages), messages
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
