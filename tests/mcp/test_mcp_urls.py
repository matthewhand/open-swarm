import importlib
import sys
from types import ModuleType

import pytest
from django.http import HttpResponse
from django.urls import path


def _stub_mcp_urls_module():
    pkg = ModuleType("django_mcp_server")
    mod = ModuleType("django_mcp_server.urls")

    def health(_request):
        return HttpResponse("OK", content_type="text/plain")

    mod.urlpatterns = [
        path("health/", health, name="mcp-health"),
    ]
    return pkg, mod


@pytest.mark.django_db
def test_mcp_urls_included_when_enabled(monkeypatch, client):
    # Enable feature
    monkeypatch.setenv("ENABLE_MCP_SERVER", "true")

    # Stub out module tree
    pkg, urls = _stub_mcp_urls_module()
    sys.modules["django_mcp_server"] = pkg
    sys.modules["django_mcp_server.urls"] = urls

    # Reload settings/urls
    settings_mod = importlib.import_module("swarm.settings")
    importlib.reload(settings_mod)
    from django.conf import settings as dj_settings
    dj_settings.ENABLE_MCP_SERVER = True

    # Clear any cached URL patterns and reload
    from django.urls import clear_url_caches
    clear_url_caches()
    urls_mod = importlib.import_module("swarm.urls")
    importlib.reload(urls_mod)

    # Request the stubbed endpoint
    resp = client.get("/mcp/health/")
    assert resp.status_code == 200
    assert resp.content == b"OK"
