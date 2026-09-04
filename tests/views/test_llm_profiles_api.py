"""API tests for GET/PATCH /v1/llm-profiles/ (REQ-43)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from django.urls import resolve
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


def _config():
    return {
        "llm": {
            "gpt-4o-mini": {"provider": "openai", "model": "gpt-4o-mini"},
            "gpt-5.6-terra": {"provider": "openai", "model": "gpt-5.6-terra"},
            "o3": {"provider": "openai", "model": "o3"},
        },
        "settings": {
            "default_llm_profile": "gpt-5.6-terra",
            "override_per_task": False,
        },
    }


def test_llm_profiles_urls_accept_trailing_slash():
    assert resolve("/v1/llm-profiles").url_name == "llm-profiles-api-no-slash"
    assert resolve("/v1/llm-profiles/").url_name == "llm-profiles-api"


class TestLlmProfilesGet:
    @patch("swarm.core.llm_task_routing.load_swarm_config", return_value=_config())
    def test_lists_configured_profiles_and_default(self, _mock_load, api_client):
        resp = api_client.get("/v1/llm-profiles/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "llm_profiles"
        ids = [row["id"] for row in data["profiles"]]
        assert "gpt-5.6-terra" in ids
        assert data["default_llm_profile"] == "gpt-5.6-terra"
        assert data["override_per_task"] is False
        blob = json.dumps(data)
        assert "api_key" not in blob
        assert "sk-" not in blob

    @patch("swarm.core.llm_task_routing.load_swarm_config", return_value={"llm": {}})
    def test_empty_catalog_is_200_with_warning(self, _mock_load, api_client):
        resp = api_client.get("/v1/llm-profiles/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["default_llm_profile"] == "default"
        assert data["warnings"]


class TestLlmProfilesPatch:
    def test_patch_empty_is_400(self, api_client):
        resp = api_client.patch("/v1/llm-profiles/", {}, format="json")
        assert resp.status_code == 400

    def test_patch_persists_default(self, api_client, tmp_path: Path):
        path = tmp_path / "swarm_config.json"
        path.write_text(json.dumps(_config()), encoding="utf-8")
        with patch("swarm.core.remotes.load_raw_config", return_value=(_config(), path)):
            resp = api_client.patch(
                "/v1/llm-profiles/",
                {
                    "default_llm_profile": "o3",
                    "override_per_task": True,
                    "task_llm_profiles": {
                        "auxiliary": "gpt-4o-mini",
                        "delegation": "o3",
                        "orchestration": "gpt-5.6-terra",
                    },
                },
                format="json",
            )
        assert resp.status_code == 200
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["settings"]["default_llm_profile"] == "o3"
        assert raw["settings"]["override_per_task"] is True
        assert resp.json()["persisted_to"] == str(path)
        assert "sk-" not in path.read_text(encoding="utf-8")
