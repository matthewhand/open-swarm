"""End-to-end API tests for the CLI fusion blueprints over /v1/chat/completions.

The per-blueprint smoke matrix proves cli_agent/moa are *reachable*, but
only with an empty config (so they answer "no CLI agents configured"). These
tests inject fake echo-based adapters via the swarm AppConfig and assert a real
panel -> synthesize flow — and that per-request `params` (cli/panel) drive
selection — across the OpenAI-compatible surface.
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
    # Param-less requests reuse get_blueprint_instance()'s instance cache. Clear
    # it before AND after each test so neither a stale empty-config instance from
    # an earlier test leaks in, nor our fake-config instance leaks out.
    from swarm.views import utils as view_utils

    view_utils._blueprint_instance_cache.clear()
    yield
    view_utils._blueprint_instance_cache.clear()


@pytest.fixture
def fake_cli_config(monkeypatch):
    cfg = {
        "cli_agents": {"a": _echo("A"), "b": _echo("B")},
        "cli_fusion": {
            "default_cli": "a",
            "default_preset": "p",
            "presets": {"p": {"panel": ["a", "b"]}},
        },
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
    return client.post("/v1/chat/completions", data=json.dumps(body), content_type="application/json")


def _content(response):
    return response.json()["choices"][0]["message"]["content"].strip()


@pytest.mark.django_db
def test_cli_fusion_panel_synthesizes_over_api(client, fake_cli_config):
    # No judge configured -> synthesize falls back to the longest panel answer.
    resp = _post(client, "moa", "hello", params={"panel": ["a", "b"]})
    assert resp.status_code == 200, resp.content[:300]
    assert resp.json().get("object") == "chat.completion"
    assert _content(resp) in ("A:hello", "B:hello")


@pytest.mark.django_db
def test_moa_uses_default_preset_without_params(client, fake_cli_config):
    resp = _post(client, "moa", "world")
    assert resp.status_code == 200, resp.content[:300]
    assert _content(resp) in ("A:world", "B:world")


@pytest.mark.django_db
def test_system_fingerprint_names_resolved_backends(client, fake_cli_config):
    # The response's system_fingerprint reports which CLI(s) actually answered,
    # not just the blueprint id — so an OpenAI client can attribute the answer.
    resp = _post(client, "moa", "hello", params={"panel": ["a", "b"], "judge": "a"})
    assert resp.status_code == 200, resp.content[:300]
    fp = resp.json().get("system_fingerprint") or ""
    assert fp.startswith("cli_fusion:")
    assert "a" in fp and "b" in fp
    assert "judge=a" in fp


@pytest.mark.django_db
def test_system_fingerprint_single_cli_agent(client, fake_cli_config):
    resp = _post(client, "cli_agent", "hello", params={"cli": "b"})
    assert resp.status_code == 200, resp.content[:300]
    assert resp.json().get("system_fingerprint") == "cli_agent:b"


@pytest.mark.django_db
def test_cli_agent_respects_cli_param_over_api(client, fake_cli_config):
    # The single-CLI blueprint should run exactly the adapter named in params.
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
def streaming_cli_config(monkeypatch):
    code = "import sys; sys.stdout.write('alpha\\nbeta\\n')"
    cfg = {
        "cli_agents": {"s": {"cmd": [PY, "-c", code, "{prompt}"], "parse": "text"}},
        "cli_fusion": {"default_cli": "s"},
    }
    monkeypatch.setattr(apps.get_app_config("swarm"), "config", cfg, raising=False)
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-test-mode")
    return cfg


@pytest.mark.django_db
def test_cli_agent_streams_incremental_deltas_over_api(client, streaming_cli_config):
    body = {
        "model": "cli_agent",
        "messages": [{"role": "user", "content": "go"}],
        "stream": True,
    }
    resp = client.post("/v1/chat/completions", data=json.dumps(body), content_type="application/json")
    assert resp.status_code == 200
    sse = _sse_text(resp)
    assert "data: [DONE]" in sse
    # The streamed deltas reassemble to the CLI's stdout.
    import re

    deltas = "".join(re.findall(r'"content":\s*"([^"]*)"', sse))
    assert "alpha" in deltas and "beta" in deltas


@pytest.mark.django_db(transaction=True)
def test_chat_completions_background_then_poll(client, fake_cli_config, monkeypatch, tmp_path):
    """Async on /v1/chat/completions: background -> 202 queued handle, poll via responses."""
    import time

    monkeypatch.setenv("SWARM_RESPONSES_DIR", str(tmp_path))
    resp = client.post(
        "/v1/chat/completions",
        data=json.dumps({
            "model": "cli_agent",
            "messages": [{"role": "user", "content": "hi"}],
            "params": {"cli": "a"},
            "background": True,
        }),
        content_type="application/json",
    )
    assert resp.status_code == 202, resp.content[:300]
    ack = resp.json()
    assert ack["status"] == "queued"
    assert ack["id"].startswith("resp_")
    assert ack["poll_url"] == f"/v1/responses/{ack['id']}"

    final = None
    for _ in range(80):
        d = client.get(f"/v1/responses/{ack['id']}").json()
        if d.get("status") in ("completed", "failed"):
            final = d
            break
        time.sleep(0.1)
    assert final is not None and final["status"] == "completed"
    assert "A:hi" in final["output_text"]
    assert isinstance(final.get("execution_ms"), int)
