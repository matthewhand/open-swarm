"""API tests for GET/PATCH /v1/config-ownership/ and /v1/config/sections/."""

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


def test_config_ownership_urls_accept_trailing_slash():
    assert resolve("/v1/config-ownership").url_name == "config-ownership-api-no-slash"
    assert resolve("/v1/config-ownership/").url_name == "config-ownership-api"
    assert resolve("/v1/config/sections/llm").url_name == "config-section-api-no-slash"
    assert resolve("/v1/config/sections/llm/").url_name == "config-section-api"


class TestConfigOwnershipGet:
    def test_lists_decision_and_inventory(self, api_client):
        resp = api_client.get("/v1/config-ownership/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "config_ownership"
        assert data["decision"] == "Full"
        assert "llm" in data["webui_sections"]
        keys = {row["key"] for row in data["inventory"]}
        assert "remotes" in keys
        assert "secrets.*" in keys
        blob = json.dumps(data)
        assert "sk-" not in blob


class TestConfigSection:
    def test_refuse_out_of_partition(self, api_client):
        resp = api_client.patch(
            "/v1/config/sections/DJANGO_SECRET_KEY/",
            {"entries": {"x": "y"}},
            format="json",
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "out_of_partition"

    def test_patch_llm_and_mcp(self, api_client, tmp_path: Path):
        path = tmp_path / "swarm_config.json"
        path.write_text(json.dumps({"llm": {}}), encoding="utf-8")
        with patch("swarm.core.remotes.load_raw_config", return_value=({"llm": {}}, path)):
            resp = api_client.patch(
                "/v1/config/sections/llm/",
                {
                    "upsert": {
                        "local": {
                            "provider": "openai",
                            "model": "llama3",
                            "api_key": "${OPENAI_API_KEY}",
                        }
                    }
                },
                format="json",
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["local"]["model"] == "llama3"
            assert resp.json()["data"]["local"]["api_key"] == "${OPENAI_API_KEY}"

            bad = api_client.patch(
                "/v1/config/sections/mcpServers/",
                {"upsert": {"x": {"command": "npx", "env": {"API_KEY": "sk-live"}}}},
                format="json",
            )
            assert bad.status_code == 400
            assert bad.json()["code"] == "plaintext_secret"

        assert "sk-live" not in path.read_text(encoding="utf-8")
