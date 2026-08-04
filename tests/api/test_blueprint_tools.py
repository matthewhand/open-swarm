"""Tests for GET /v1/blueprints/<id>/tools (capability -> MCP provider resolution)."""

import pytest


@pytest.fixture(autouse=True)
def _no_host_config(monkeypatch):
    # Make resolution deterministic: no user config -> capabilities auto-provision
    # the non-auth catalog providers (duckduckgo / playwright).
    monkeypatch.setattr("swarm.core.config_loader.find_config_file", lambda *a, **k: None)


@pytest.mark.django_db
def test_blueprint_with_tool_requirements_resolves_to_non_auth(client):
    data = client.get("/v1/blueprints/whiskeytango_foxtrot/tools").json()
    assert data["blueprint"] == "whiskeytango_foxtrot"
    # declared: browser mandatory, web_search optional
    assert data["requirements"]["browser"] == "mandatory"
    assert data["ok"] is True
    # mandatory browser auto-provisions the non-auth official playwright-mcp
    assert data["satisfied"]["browser"] == "playwright"
    assert "playwright" in data["servers"]
    assert data["servers"]["playwright"]["command"] == "npx"


@pytest.mark.django_db
def test_blueprint_without_tool_requirements_is_empty_but_ok(client):
    data = client.get("/v1/blueprints/cli_agent/tools").json()
    assert data["requirements"] == {}
    assert data["ok"] is True
    assert data["servers"] == {}


@pytest.mark.django_db
def test_unknown_blueprint_404(client):
    assert client.get("/v1/blueprints/definitely_not_real_zzz/tools").status_code == 404
