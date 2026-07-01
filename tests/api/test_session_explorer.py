"""Session Explorer web UI: list_summaries data layer + the list/detail/API views."""
from __future__ import annotations

import json

import pytest
from django.urls import reverse

from swarm.core import responses_store


def _save(rid, *, status="completed", model="hybrid_team", output="hello", progress=None, created=1):
    responses_store.save({
        "id": rid, "object": "response",
        "response": {
            "id": rid, "model": model, "status": status, "created_at": created,
            "output_text": output, "execution_ms": 42,
            "progress": progress or [],
        },
        "messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": output}],
    })


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_RESPONSES_DIR", str(tmp_path))
    return tmp_path


def test_list_summaries_newest_first(store):
    _save("resp_a", created=1, output="first")
    _save("resp_b", created=5, output="second", progress=[{"role": "agent", "status": "completed"}])
    rows = responses_store.list_summaries()
    assert [r["id"] for r in rows] == ["resp_b", "resp_a"]  # newest first
    assert rows[0]["delegations"] == [{"role": "agent", "status": "completed"}]


@pytest.mark.django_db
def test_session_explorer_list_view(client, store):
    _save("resp_x", output="explorer-marker")
    resp = client.get(reverse("session-explorer"))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Session Explorer" in body and "resp_x" in body and "explorer-marker" in body


@pytest.mark.django_db
def test_session_detail_view_shows_delegations(client, store):
    _save("resp_d", progress=[
        {"role": "agent", "status": "completed", "result": "coded", "model_used": "qwen3.5"},
        {"role": "auxiliary", "status": "failed", "error": "boom"},
    ])
    resp = client.get(reverse("session-detail", kwargs={"response_id": "resp_d"}))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Timeline" in body and "agent" in body and "auxiliary" in body
    assert "coded" in body and "boom" in body


@pytest.mark.django_db
def test_session_detail_404(client, store):
    assert client.get(reverse("session-detail", kwargs={"response_id": "resp_nope"})).status_code == 404


@pytest.mark.django_db
def test_session_list_api(client, store):
    _save("resp_api")
    resp = client.get(reverse("session-list-api"))
    assert resp.status_code == 200
    data = json.loads(resp.content)
    assert any(s["id"] == "resp_api" for s in data["sessions"])
