"""Parity: /v1/responses drives hybrid_team end-to-end, same as chat_completions.

Proves the Responses API runs the flagship blueprint's full flow (REST coordinator
+ grok persona + consensus panel) through the async-by-default worker — so the
claude-orchestrated delegation machinery is reachable on Responses too. Determin-
istic via SWARM_TEST_MODE (REST stub) + fake echo CLIs (no model/network).
"""
from __future__ import annotations

import json
import sys

import pytest
from django.apps import apps

PY = sys.executable


def _echo(prefix: str) -> dict:
    return {"cmd": [PY, "-c", f"import sys; print('{prefix}:' + sys.argv[1])", "{prompt}"]}


@pytest.fixture(autouse=True)
def _isolate_blueprint_cache():
    from swarm.views import utils as view_utils
    view_utils._blueprint_instance_cache.clear()
    yield
    view_utils._blueprint_instance_cache.clear()


@pytest.fixture
def hybrid_config(monkeypatch):
    cfg = {
        "cli_agents": {"grok": _echo("GROK"), "a": _echo("A"), "b": _echo("B")},
        "hybrid_team": {"grok": "grok", "panel": ["a", "b"]},
    }
    app = apps.get_app_config("swarm")
    monkeypatch.setattr(app, "config", cfg, raising=False)
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-test-mode")
    return cfg


@pytest.mark.django_db(transaction=True)
def test_responses_runs_hybrid_team_end_to_end(client, hybrid_config):
    resp = client.post(
        "/v1/responses",
        data=json.dumps({"model": "hybrid_team", "input": "hi"}),
        content_type="application/json",
    )
    # Fast under SWARM_TEST_MODE -> the async-default worker completes inside the
    # sync window and returns the result inline.
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    text = body["output_text"]
    assert "[rest-plan] hi" in text                 # REST coordinator ran via Responses
    assert "GROK:" in text                           # grok persona delegated
    assert ("A:" in text) or ("B:" in text)          # consensus panel ran
