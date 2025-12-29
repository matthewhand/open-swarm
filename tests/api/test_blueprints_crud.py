import json

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_custom_blueprints_crud(monkeypatch, client):
    # In-memory library
    lib = {"installed": [], "custom": []}

    from swarm.views import api_views as av
    from swarm.views import blueprint_library_views as blv

    def fake_get_lib():
        return lib

    def fake_save_lib(newlib):
        lib.clear()
        lib.update(newlib)
        return True

    # Patch both the source module and the API module that imported the symbols
    monkeypatch.setattr(blv, "get_user_blueprint_library", fake_get_lib)
    monkeypatch.setattr(blv, "save_user_blueprint_library", fake_save_lib)
    monkeypatch.setattr(av, "get_user_blueprint_library", fake_get_lib)
    monkeypatch.setattr(av, "save_user_blueprint_library", fake_save_lib)

    # Create
    url = reverse("custom-blueprints")
    resp = client.post(
        url,
        data=json.dumps({
            "name": "Demo Analyzer",
            "description": "Analyze",
            "tags": ["demo"],
            "required_mcp_servers": ["filesystem"],
            "env_vars": ["ALLOWED_PATH"],
        }),
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.content
    created = resp.json()
    bp_id = created["id"]

    # List to verify presence
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert any(i["id"] == bp_id for i in data)
