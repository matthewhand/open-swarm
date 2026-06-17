"""Tests for the Builder config-options endpoint (GET /v1/config-options/)."""

import pytest


@pytest.mark.django_db
def test_config_options_exposes_all_decoupling_primitives(client):
    data = client.get("/v1/config-options/").json()

    # Skills the UI can offer for the skill= param (with full SKILL.md body).
    names = {s["name"] for s in data["skills"]}
    assert {"conventional-commit", "counting-lines"} <= names
    cc = next(s for s in data["skills"] if s["name"] == "conventional-commit")
    assert cc["instructions"] and "Conventional Commit" in cc["instructions"]

    # Inference: axes + per-provider and per-model traits + model flags.
    inf = data["inference"]
    assert inf["traits"] == ["intelligence", "speed", "cost"]
    assert {"grok", "claude", "gemini"} <= set(inf["cli_traits"])
    assert "gemini-3-pro-preview" in inf["model_traits"]
    assert inf["model_flags"]["gemini"] == "-m"

    # Tools: capabilities + MCP catalog with auth flags (playwright non-auth).
    tools = data["tools"]
    assert {"web_search", "browser"} <= set(tools["capabilities"])
    by_name = {m["name"]: m for m in tools["mcp_catalog"]}
    assert by_name["playwright"]["needs_auth"] is False
    assert "browser" in by_name["playwright"]["provides"]
    assert by_name["brave-search"]["needs_auth"] is True
