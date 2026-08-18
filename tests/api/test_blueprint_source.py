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
    # Traversal outside the blueprint dir must 404 — never fall back to primary.
    resp = client.get("/v1/blueprints/cli_fusion/source", {"file": "../../settings.py"})
    assert resp.status_code == 404
    assert "error" in resp.json()


@pytest.mark.django_db
def test_source_missing_file_returns_404(client):
    """Explicit ?file= for a missing name is 404, not a silent primary fallback."""
    resp = client.get("/v1/blueprints/cli_fusion/source", {"file": "does_not_exist.py"})
    assert resp.status_code == 404
    assert resp.json()["error"] == "file not found: does_not_exist.py"


@pytest.mark.django_db
def test_source_selects_requested_file(client):
    resp = client.get("/v1/blueprints/cli_fusion/source", {"file": "README.md"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["selected"] == "README.md"
    assert data["primary"] == "blueprint_cli_fusion.py"
    assert len(data["content"]) > 0


@pytest.mark.django_db
def test_cli_agents_endpoint_exposes_native_consensus(client):
    resp = client.get("/v1/cli-agents/")
    assert resp.status_code == 200
    data = resp.json()
    assert "grok" in data["clis"]
    assert data["native_consensus"]["grok"] == ["--best-of-n", "{n}"]
    assert data["catalog"]["grok"]["parse"] == "json:.text"
