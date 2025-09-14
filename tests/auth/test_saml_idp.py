import importlib
import sys
from types import ModuleType

import pytest
from django.http import HttpResponse
from django.urls import path, resolve


def _stub_idp_urls_module():
    mod_pkg = ModuleType("djangosaml2idp")
    mod_urls = ModuleType("djangosaml2idp.urls")

    def metadata_view(_request):
        return HttpResponse("OK", content_type="text/plain")

    mod_urls.urlpatterns = [
        path("metadata/", metadata_view, name="saml-idp-metadata"),
    ]
    return mod_pkg, mod_urls


@pytest.mark.django_db
def test_idp_urls_included_when_enabled(monkeypatch, client):
    # Enable feature
    monkeypatch.setenv("ENABLE_SAML_IDP", "true")

    # Stub out djangosaml2idp import tree
    mod_pkg, mod_urls = _stub_idp_urls_module()
    sys.modules["djangosaml2idp"] = mod_pkg
    sys.modules["djangosaml2idp.urls"] = mod_urls

    # Reload settings and also set flag on django.conf.settings (object is cached)
    settings_mod = importlib.import_module("swarm.settings")
    importlib.reload(settings_mod)
    from django.conf import settings as dj_settings
    setattr(dj_settings, "ENABLE_SAML_IDP", True)
    urls_mod = importlib.import_module("swarm.urls")
    importlib.reload(urls_mod)

    # Request the stubbed metadata endpoint via /idp/
    resp = client.get("/idp/metadata/")
    assert resp.status_code == 200
    assert resp.content == b"OK"


def test_idp_config_structure_present_when_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_SAML_IDP", "true")
    settings_mod = importlib.import_module("swarm.settings")
    importlib.reload(settings_mod)
    # Ensure the template mapping exists for downstream configuration
    assert hasattr(settings_mod, "SAML_IDP_SPCONFIG")
    assert isinstance(getattr(settings_mod, "SAML_IDP_SPCONFIG"), dict)
