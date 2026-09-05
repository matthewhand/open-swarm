"""GET /v1/blueprints/<id>/personas — declared roster (REQ-81). No live host."""

import uuid
from pathlib import Path

import pytest
from django.urls import resolve
from rest_framework.test import APIClient

from swarm.core.persona_parse import parse_openai_agent_personas

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "openai_agents_personas"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def isolated_custom_blueprint(tmp_path, monkeypatch):
    """Isolate custom-blueprint create/teardown (unique tmp library + registry)."""
    from swarm.views import api_views
    from swarm.views import blueprint_library_views as lib

    monkeypatch.setattr(lib, "get_user_config_dir_for_swarm", lambda: tmp_path)
    api_views._custom_blueprints_registry.clear()
    yield tmp_path
    api_views._custom_blueprints_registry.clear()


def _unique_blueprint_name(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


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
def test_custom_three_agent_fixture_via_api(api_client, isolated_custom_blueprint):
    code = (FIXTURES / "three_agents.py").read_text(encoding="utf-8")
    name = _unique_blueprint_name("req81_triad")
    created = api_client.post(
        "/v1/blueprints/custom/",
        {
            "name": name,
            "description": "REQ-81 fixture",
            "code": code,
        },
        format="json",
    )
    assert created.status_code == 201
    bp_id = created.json()["id"]
    resp = api_client.get(f"/v1/blueprints/{bp_id}/personas")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert [p["name"] for p in data["personas"]] == ["Researcher", "Writer", "Reviewer"]


@pytest.mark.django_db
def test_garbage_custom_blueprint_is_one_generic(api_client, isolated_custom_blueprint):
    name = _unique_blueprint_name("req81_junk")
    created = api_client.post(
        "/v1/blueprints/custom/",
        {
            "name": name,
            "code": (FIXTURES / "garbage.py").read_text(encoding="utf-8"),
        },
        format="json",
    )
    assert created.status_code == 201
    bp_id = created.json()["id"]
    resp = api_client.get(f"/v1/blueprints/{bp_id}/personas")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["personas"] == []
    assert "FakeInvented" not in str(data)


@pytest.mark.django_db
def test_custom_fixture_teardown_leaves_empty_custom_list(api_client, isolated_custom_blueprint):
    """#826: leftover create must not fill GET /v1/blueprints/custom/ when empty."""
    from unittest.mock import patch

    from swarm.views import api_views

    created = api_client.post(
        "/v1/blueprints/custom/",
        {
            "name": _unique_blueprint_name("req81_leak"),
            "code": "# isolated",
        },
        format="json",
    )
    assert created.status_code == 201
    api_views._custom_blueprints_registry.clear()
    with patch(
        "swarm.views.api_views.get_user_blueprint_library",
        return_value={"installed": [], "custom": []},
    ):
        resp = api_client.get("/v1/blueprints/custom/")
    assert resp.status_code == 200
    assert resp.json() == {"object": "list", "data": []}


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
