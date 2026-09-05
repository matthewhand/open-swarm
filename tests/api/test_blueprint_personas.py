"""GET /v1/blueprints/<id>/personas — declared roster (REQ-81). No live host."""

from pathlib import Path

import pytest
from django.urls import resolve
from rest_framework.test import APIClient

from swarm.core.persona_parse import parse_openai_agent_personas

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "openai_agents_personas"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _isolate_custom_blueprint_registry():
    """POST /v1/blueprints/custom/ also fills the process-wide fallback list."""
    from swarm.views import api_views

    snapshot = list(api_views._custom_blueprints_registry)
    api_views._custom_blueprints_registry.clear()
    yield
    api_views._custom_blueprints_registry.clear()
    api_views._custom_blueprints_registry.extend(snapshot)


def test_personas_urls_accept_trailing_slash():
    assert resolve("/v1/blueprints/software_dev/personas").url_name == "blueprint-personas"
    assert resolve("/v1/blueprints/software_dev/personas/").url_name == "blueprint-personas-slash"


@pytest.mark.django_db
def test_software_dev_personas_are_three_named_seats(api_client):
    resp = api_client.get("/v1/blueprints/software_dev/personas")
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "blueprint.personas"
    assert data["count"] == 3
    names = [p["name"] for p in data["personas"]]
    assert names == ["engineer", "skeptic", "coding-requirements-gate"]


@pytest.mark.django_db
def test_custom_three_agent_fixture_via_api(api_client, tmp_path, monkeypatch):
    from swarm.views import blueprint_library_views as lib

    monkeypatch.setattr(lib, "get_user_config_dir_for_swarm", lambda: tmp_path)

    code = (FIXTURES / "three_agents.py").read_text(encoding="utf-8")
    created = api_client.post(
        "/v1/blueprints/custom/",
        {
            "name": "triad",
            "description": "REQ-81 fixture",
            "code": code,
        },
        format="json",
    )
    assert created.status_code == 201
    resp = api_client.get("/v1/blueprints/triad/personas")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert [p["name"] for p in data["personas"]] == ["Researcher", "Writer", "Reviewer"]


@pytest.mark.django_db
def test_garbage_custom_blueprint_is_one_generic(api_client, tmp_path, monkeypatch):
    from swarm.views import blueprint_library_views as lib

    monkeypatch.setattr(lib, "get_user_config_dir_for_swarm", lambda: tmp_path)

    created = api_client.post(
        "/v1/blueprints/custom/",
        {
            "name": "junk",
            "code": (FIXTURES / "garbage.py").read_text(encoding="utf-8"),
        },
        format="json",
    )
    assert created.status_code == 201
    resp = api_client.get("/v1/blueprints/junk/personas")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["personas"] == []
    assert "FakeInvented" not in str(data)


@pytest.mark.django_db
def test_unknown_blueprint_personas_404(api_client):
    assert api_client.get("/v1/blueprints/definitely_not_a_blueprint_zzz/personas").status_code == 404


@pytest.mark.django_db
def test_blueprints_list_includes_persona_count(api_client):
    resp = api_client.get("/v1/blueprints/")
    assert resp.status_code == 200
    rows = {row["id"]: row for row in resp.json()["data"]}
    assert "software_dev" in rows
    assert rows["software_dev"]["persona_count"] == 3
    assert [p["name"] for p in rows["software_dev"]["personas"]] == [
        "engineer",
        "skeptic",
        "coding-requirements-gate",
    ]


@pytest.mark.django_db
def test_source_payload_includes_personas(api_client):
    resp = api_client.get("/v1/blueprints/software_dev/source")
    assert resp.status_code == 200
    data = resp.json()
    assert data["persona_count"] == 3
    assert len(data["personas"]) == 3


def test_parser_matches_api_fixture_contract():
    """Own-diff lock: API shape is the same object the parser returns."""
    parsed = parse_openai_agent_personas(
        (FIXTURES / "three_agents.py").read_text(encoding="utf-8")
    )
    assert parsed["count"] == 3
    assert {p["name"] for p in parsed["personas"]} == {"Researcher", "Writer", "Reviewer"}
