import importlib

import pytest
from django.urls import resolve


@pytest.mark.django_db
def test_idp_urls_resolve_when_package_available(monkeypatch):
    # Skip unless real package is present
    pytest.importorskip("djangosaml2idp")

    # Enable feature
    monkeypatch.setenv("ENABLE_SAML_IDP", "true")

    # Reload settings/urls to apply flag
    settings_mod = importlib.import_module("swarm.settings")
    importlib.reload(settings_mod)
    urls_mod = importlib.import_module("swarm.urls")
    importlib.reload(urls_mod)

    # Ensure metadata route is present without invoking the view
    match = resolve("/idp/metadata/")
    assert match is not None
    assert "djangosaml2idp" in getattr(match.func, "__module__", "")

