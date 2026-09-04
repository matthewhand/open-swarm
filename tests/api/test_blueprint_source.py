"""Tests for the read-only blueprint source endpoint (GET /v1/blueprints/<id>/source)."""

import pytest
from django.urls import resolve


def test_blueprint_source_and_cli_agents_urls_accept_trailing_slash():
    """Slash + no-slash twins (same pattern as /v1/responses and /v1/chat/completions)."""
    assert resolve("/v1/blueprints/cli_fusion/source").url_name == "blueprint-source"
    assert resolve("/v1/blueprints/cli_fusion/source/").url_name == "blueprint-source-slash"
    assert resolve("/blueprint-library/cli_fusion/source/").url_name == "blueprint_source"
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
def test_source_html_accept_is_pretty_python_not_json(client):
    """Browsers asking for HTML get highlighted Python, not the JSON envelope."""
    resp = client.get(
        "/v1/blueprints/cli_fusion/source/",
        HTTP_ACCEPT="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    )
    assert resp.status_code == 200
    assert "application/json" not in resp["Content-Type"]
    html = resp.content.decode()
    assert "language-python" in html
    assert "class CliFusionBlueprint" in html
    assert '"content":' not in html
    assert html.strip()[:1] != "{"


@pytest.mark.django_db
def test_source_json_accept_stays_json(client):
    resp = client.get(
        "/v1/blueprints/cli_fusion/source/",
        HTTP_ACCEPT="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "cli_fusion"
    assert "class CliFusionBlueprint" in data["content"]


@pytest.mark.django_db
def test_library_source_page_is_pretty_python(client, test_user):
    client.force_login(test_user)
    resp = client.get("/blueprint-library/cli_fusion/source/")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "language-python" in html
    assert "class CliFusionBlueprint" in html
    assert '"primary":' not in html


@pytest.mark.django_db
def test_cli_agents_endpoint_exposes_native_consensus(client):
    resp = client.get("/v1/cli-agents/")
    assert resp.status_code == 200
    data = resp.json()
    assert "grok" in data["clis"]
    assert data["native_consensus"]["grok"] == ["--best-of-n", "{n}"]
    assert data["catalog"]["grok"]["parse"] == "json:.text"
    assert data["list_models"]["opencode"] == ["opencode", "models"]
    assert data["list_models"]["gemini"] == ["gemini", "--list-models"]
    assert data["list_models"]["codex"] == ["codex", "debug", "models"]


@pytest.mark.django_db
def test_cli_agent_models_urls_accept_trailing_slash():
    assert resolve("/v1/cli-agents/models").url_name == "cli-agent-models-all-no-slash"
    assert resolve("/v1/cli-agents/models/").url_name == "cli-agent-models-all"
    assert resolve("/v1/cli-agents/grok/models").url_name == "cli-agent-models-no-slash"
    assert resolve("/v1/cli-agents/grok/models/").url_name == "cli-agent-models"


@pytest.mark.django_db
def test_cli_agent_models_single_cli(client, monkeypatch):
    from swarm.core.cli_models import ListModelsResult

    monkeypatch.setattr(
        "swarm.core.cli_models.list_models",
        lambda name, **_k: ListModelsResult(cli=name, models=["grok-4"]),
    )
    resp = client.get("/v1/cli-agents/grok/models")
    assert resp.status_code == 200
    assert resp.json() == {"cli": "grok", "models": ["grok-4"]}


@pytest.mark.django_db
def test_cli_agent_models_unknown_cli_empty_warning(client, monkeypatch):
    from swarm.core.cli_models import ListModelsResult

    monkeypatch.setattr(
        "swarm.core.cli_models.list_models",
        lambda name, **_k: ListModelsResult(
            cli=name, models=[], warning="unknown CLI 'nope'"
        ),
    )
    resp = client.get("/v1/cli-agents/nope/models/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cli"] == "nope"
    assert data["models"] == []
    assert "unknown" in data["warning"]


@pytest.mark.django_db
def test_cli_agent_models_all(client, monkeypatch):
    from swarm.core.cli_models import ListModelsResult

    monkeypatch.setattr(
        "swarm.core.cli_models.list_models_all",
        lambda **_k: [
            ListModelsResult(cli="claude", models=[], warning="not installed"),
            ListModelsResult(cli="opencode", models=["opencode/big-pickle"]),
        ],
    )
    resp = client.get("/v1/cli-agents/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["models"] == []
    assert data[1] == {"cli": "opencode", "models": ["opencode/big-pickle"]}
