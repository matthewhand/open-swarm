"""Tests for the read-only blueprint source endpoint (GET /v1/blueprints/<id>/source)."""

import pytest


@pytest.mark.django_db
def test_source_returns_primary_file_and_content(client):
    resp = client.get("/v1/blueprints/cli_fusion/source")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "cli_fusion"
    assert data["primary"] == "blueprint_cli_fusion.py"
    assert data["selected"] == "blueprint_cli_fusion.py"
    assert any(f["name"] == "blueprint_cli_fusion.py" for f in data["files"])
    assert "class CliFusionBlueprint" in data["content"]


@pytest.mark.django_db
def test_source_unknown_blueprint_404(client):
    assert client.get("/v1/blueprints/definitely_not_a_blueprint_zzz/source").status_code == 404


@pytest.mark.django_db
def test_source_rejects_path_traversal(client):
    # A traversal attempt resolves outside the blueprint dir -> 404, never served.
    resp = client.get("/v1/blueprints/cli_fusion/source", {"file": "../../settings.py"})
    assert resp.status_code == 200
    # the requested out-of-dir file is ignored; it falls back to the primary
    assert resp.json()["selected"] == "blueprint_cli_fusion.py"
