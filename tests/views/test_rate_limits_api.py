"""REQ-88 /v1/rate-limits/ — persist on the provider, no secrets, no Neon."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.urls import resolve
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def swarm_config(tmp_path, monkeypatch):
    path = tmp_path / "swarm_config.json"
    path.write_text(
        json.dumps(
            {
                "llm": {
                    "local": {
                        "provider": "openai",
                        "model": "stub",
                        "api_key": "${OPENAI_API_KEY}",
                    }
                },
                "cli_agents": {"stub": {"cmd": ["echo"]}},
                "remotes": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SWARM_CONFIG_PATH", str(path))
    return path


def test_rate_limits_urls_accept_trailing_slash():
    assert resolve("/v1/rate-limits").url_name == "rate-limits-api-no-slash"
    assert resolve("/v1/rate-limits/").url_name == "rate-limits-api"


def test_get_lists_provider_rows(api_client: APIClient, swarm_config: Path):
    resp = api_client.get("/v1/rate-limits/")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["object"] == "provider_rate_limits"
    ids = {row["id"] for row in payload["data"]}
    assert "cli:stub" in ids
    assert "llm:local" in ids
    stub = next(row for row in payload["data"] if row["id"] == "cli:stub")
    assert stub["rules"]["messages_per_minute"] is None
    blob = json.dumps(payload)
    assert "sk-" not in blob
    assert "Django" not in blob


def test_patch_persists_on_provider(api_client: APIClient, swarm_config: Path):
    resp = api_client.patch(
        "/v1/rate-limits/",
        {"provider": "cli:stub", "rules": {"messages_per_minute": 1, "tokens_per_day": 5000}},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    assert resp.json()["saved"]["messages_per_minute"] == 1
    stored = json.loads(swarm_config.read_text(encoding="utf-8"))
    assert stored["cli_agents"]["stub"]["rate_limits"]["messages_per_minute"] == 1
    assert stored["cli_agents"]["stub"]["cmd"] == ["echo"]
    assert stored["cli_agents"]["stub"]["rate_limits"]["tokens_per_day"] == 5000
