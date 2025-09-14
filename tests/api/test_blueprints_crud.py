import json
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_custom_blueprints_crud(monkeypatch, client):
    # In-memory library
    lib = {"installed": [], "custom": []}

    from swarm.views import blueprint_library_views as blv
    from swarm.views import api_views as av

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

    # List with search
    resp = client.get(url + "?search=demo")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert any(i["id"] == bp_id for i in data)

    # Get single
    detail = reverse("custom-blueprint-detail", kwargs={"blueprint_id": bp_id})
    resp = client.get(detail)
    assert resp.status_code == 200
    assert resp.json()["id"] == bp_id

    # Patch
    resp = client.patch(
        detail,
        data=json.dumps({"tags": ["demo", "analysis"]}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["demo", "analysis"]

    # Delete
    resp = client.delete(detail)
    assert resp.status_code == 204
    # Verify deletion
    resp = client.get(detail)
    assert resp.status_code == 404
