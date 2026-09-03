"""API tests for REQ-42 definition context + summarise."""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from swarm.core.definition_explain import REQ42_INJECTED_FIXTURE


@pytest.fixture
def api_client():
    return APIClient()


def test_get_definition_returns_explanation_without_llm(api_client, monkeypatch):
    monkeypatch.delenv("LITELLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("DEFAULT_LLM", raising=False)
    response = api_client.get("/v1/definitions/role/gate/")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "gate"
    assert body["kind"] == "role"
    assert "YES/NO" in body["explanation"]
    assert body["source"]
    assert "def classify" not in body["explanation"]
    assert body["default_llm"]["configured"] is False


def test_summarize_with_stub_llm_includes_injected_fixture(api_client, monkeypatch):
    monkeypatch.setenv("DEFAULT_LLM", "stub-llm")

    def fake_summarise(kind, definition_id, **kwargs):
        extra = kwargs.get("extra") or REQ42_INJECTED_FIXTURE
        return {
            "kind": kind,
            "id": definition_id,
            "configured": True,
            "model": "stub-llm",
            "summary": f"LLM summary includes {extra}",
            "injected_extra": extra,
        }

    with patch(
        "swarm.views.definition_views.summarise_definition",
        side_effect=fake_summarise,
    ):
        response = api_client.post(
            "/v1/definitions/role/gate/summarize",
            {"extra": REQ42_INJECTED_FIXTURE},
            format="json",
        )
    assert response.status_code == 200
    body = response.json()
    assert REQ42_INJECTED_FIXTURE in body["summary"]
    assert body["configured"] is True


def test_unknown_kind_404(api_client):
    response = api_client.get("/v1/definitions/widget/x/")
    assert response.status_code == 404
