"""Tests for the read-only blueprint source endpoint (GET /v1/blueprints/<id>/source)."""

import pytest
from django.urls import resolve


def test_blueprint_source_and_cli_agents_urls_accept_trailing_slash():
    """Slash + no-slash twins (same pattern as /v1/responses and /v1/chat/completions)."""
    assert resolve("/v1/blueprints/cli_fusion/source").url_name == "blueprint-source"
    assert resolve("/v1/blueprints/cli_fusion/source/").url_name == "blueprint-source-slash"
    assert resolve("/v1/cli-agents").url_name == "cli-agents-api-no-slash"
    assert resolve("/v1/cli-agents/").url_name == "cli-agents-api"


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


@pytest.mark.django_db
def test_cli_agents_endpoint_exposes_installed_and_configured(client, monkeypatch):
    """Chat CLI dropdown reads installed (host PATH) + configured (swarm_config)."""
    from django.apps import apps

    from swarm.core import cli_catalog

    monkeypatch.setattr(cli_catalog, "installed_catalog_clis", lambda: ["grok", "claude"])
    swarm_cfg = apps.get_app_config("swarm")
    monkeypatch.setattr(
        swarm_cfg,
        "config",
        {"cli_agents": {"grok": {}, "custom_cli": {}}},
    )
    resp = client.get("/v1/cli-agents/")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["installed"]) >= {"grok", "claude"}
    assert data["configured"] == ["custom_cli", "grok"]
    assert "grok" in data["clis"]


@pytest.mark.django_db
def test_cli_agents_endpoint_includes_non_catalog_path_cli(client, monkeypatch):
    """A PATH/config CLI such as antigravity must appear even outside the catalog."""
    from django.apps import apps

    from swarm.core import cli_catalog

    monkeypatch.setattr(cli_catalog, "installed_catalog_clis", lambda: ["grok"])
    monkeypatch.setattr(
        cli_catalog.shutil,
        "which",
        lambda name: "/usr/bin/antigravity" if name == "antigravity" else None,
    )
    swarm_cfg = apps.get_app_config("swarm")
    monkeypatch.setattr(
        swarm_cfg,
        "config",
        {
            "cli_agents": {"antigravity": {"cmd": ["antigravity"]}},
            "cli_fusion": {"default_cli": "antigravity"},
        },
    )
    resp = client.get("/v1/cli-agents/")
    assert resp.status_code == 200
    data = resp.json()
    assert "antigravity" in data["installed"]
    assert "antigravity" in data["configured"]
    assert data["default_cli"] == "antigravity"
    assert "antigravity" not in data["clis"]
