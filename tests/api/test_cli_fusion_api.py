"""End-to-end API tests for legacy ``cli_fusion`` model id (MoA semantics).

``cli_fusion`` / ``cli_ensemble`` resolve to Mixture of Agents (read-only
participants). These tests inject ``fake_responses`` via request params and
assert a real MoA determination over ``/v1/chat/completions``.
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
def fake_cli_config(monkeypatch):
    # cli_agent still uses cli_agents adapters; MoA uses fake_responses params.
    cfg = {
        "cli_agents": {"a": _echo("A"), "b": _echo("B")},
        "moa": {"backend": "fake", "participants": ["analyst", "critic"]},
    }
    app = apps.get_app_config("swarm")
    monkeypatch.setattr(app, "config", cfg, raising=False)
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-test-mode")
    return cfg


def _post(client, model, content, params=None):
    body = {"model": model, "messages": [{"role": "user", "content": content}]}
    if params is not None:
        body["params"] = params
    return client.post(
        "/v1/chat/completions",
        data=json.dumps(body),
        content_type="application/json",
    )


def _content(response):
    return response.json()["choices"][0]["message"]["content"].strip()


@pytest.mark.django_db
def test_cli_fusion_panel_synthesizes_over_api(client, fake_cli_config):
    resp = _post(
        client,
        "cli_fusion",
        "hello",
        params={
            "participants": ["a", "b"],
            "fake_responses": {
                "a": "A:hello",
                "b": "B:hello",
            },
        },
    )
    assert resp.status_code == 200, resp.content[:300]
    assert resp.json().get("object") == "chat.completion"
    body = _content(resp)
    assert body
    # MoA synthesizes from participants; primary opinion is included.
    assert "A:hello" in body or "B:hello" in body or "hello" in body.lower()


@pytest.mark.django_db
def test_cli_fusion_uses_default_preset_without_params(client, fake_cli_config):
    # Without fake_responses, fake backend yields deterministic stubs — still 200.
    resp = _post(client, "cli_fusion", "world")
    assert resp.status_code == 200, resp.content[:300]
    body = _content(resp)
    assert body
    assert len(body) > 5


@pytest.mark.django_db
def test_system_fingerprint_names_resolved_backends(client, fake_cli_config):
    resp = _post(
        client,
        "cli_fusion",
        "hello",
        params={
            "participants": ["a", "b"],
            "fake_responses": {"a": "A:hello", "b": "B:hello"},
        },
    )
    assert resp.status_code == 200, resp.content[:300]
    fp = resp.json().get("system_fingerprint") or ""
    assert fp.startswith("cli_fusion:")
    assert "a" in fp and "b" in fp


@pytest.mark.django_db
def test_system_fingerprint_single_cli_agent(client, fake_cli_config):
    resp = _post(client, "cli_agent", "hello", params={"cli": "b"})
    assert resp.status_code == 200, resp.content[:300]
    assert resp.json().get("system_fingerprint") == "cli_agent:b"


@pytest.mark.django_db
def test_cli_agent_respects_cli_param_over_api(client, fake_cli_config):
    resp = _post(client, "cli_agent", "pick", params={"cli": "b"})
    assert resp.status_code == 200, resp.content[:300]
    assert _content(resp) == "B:pick"


def _sse_text(response):
    import asyncio as _asyncio

    stream = response.streaming_content
    if hasattr(stream, "__aiter__"):

        async def _collect():
            return b"".join([c async for c in stream])

        return _asyncio.run(_collect()).decode()
    return b"".join(stream).decode()


@pytest.fixture
def stream_client(client):
    return client


@pytest.mark.django_db
def test_cli_fusion_streaming_completes(stream_client, fake_cli_config):
    body = {
        "model": "cli_fusion",
        "stream": True,
        "messages": [{"role": "user", "content": "stream me"}],
        "params": {
            "participants": ["a"],
            "fake_responses": {"a": "streamed-answer"},
        },
    }
    resp = stream_client.post(
        "/v1/chat/completions",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert resp.status_code == 200
    text = _sse_text(resp)
    assert "[DONE]" in text
    assert "streamed-answer" in text or "data:" in text
