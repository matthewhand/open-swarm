"""Async control-plane tests: cancellation, restart-resume, and the no-auth opt-out."""

from __future__ import annotations

import json
import time

import pytest
from django.urls import reverse
from rest_framework import status

from swarm.core import responses_store
from swarm.views import responses_views as rv


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    monkeypatch.setenv("SWARM_RESPONSES_DIR", str(tmp_path))
    monkeypatch.setattr("swarm.views.responses_views.validate_model_access", lambda *a, **k: True)


def _save_state(rid, status_str, *, with_task=True):
    rec = {
        "id": rid,
        "object": "response",
        "response": {"id": rid, "object": "response", "status": status_str, "output": [], "output_text": ""},
        "messages": None,
    }
    if with_task:
        rec["_task"] = {"request_id": rid.removeprefix("resp_"), "model": "chatbot",
                        "messages": [{"role": "user", "content": "ping"}], "params": None,
                        "previous_response_id": None}
    responses_store.save(rec)


# --- cancellation endpoint -------------------------------------------------- #

@pytest.mark.django_db(transaction=True)
class TestCancel:
    @pytest.mark.asyncio
    async def test_cancel_unknown_is_404(self, async_client):
        url = reverse("responses-cancel", kwargs={"response_id": "resp_nope"})
        resp = await async_client.post(url, SERVER_NAME="localhost")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_cancel_in_progress_marks_cancelled(self, async_client):
        rid = "resp_inflight1"
        _save_state(rid, "in_progress")
        url = reverse("responses-cancel", kwargs={"response_id": rid})
        resp = await async_client.post(url, SERVER_NAME="localhost")
        assert resp.status_code == status.HTTP_200_OK
        assert json.loads(resp.content)["status"] == "cancelled"
        # And the stored record reflects it for a poller.
        got = await async_client.get(reverse("responses-detail", kwargs={"response_id": rid}), SERVER_NAME="localhost")
        assert json.loads(got.content)["status"] == "cancelled"
        rv._clear_cancel(rid)

    @pytest.mark.asyncio
    async def test_cancel_completed_is_noop(self, async_client):
        rid = "resp_done1"
        _save_state(rid, "completed", with_task=False)
        url = reverse("responses-cancel", kwargs={"response_id": rid})
        resp = await async_client.post(url, SERVER_NAME="localhost")
        assert resp.status_code == status.HTTP_200_OK
        assert json.loads(resp.content)["status"] == "completed"  # unchanged


# --- worker honors a pre-requested cancel ----------------------------------- #

@pytest.mark.django_db(transaction=True)
def test_worker_honors_precancel():
    rid = "resp_precancel"
    rv._request_cancel(rid)
    try:
        rv._run_background_response(rid, "precancel", "chatbot", [{"role": "user", "content": "x"}], None, None)
        rec = responses_store.load(rid)
        assert rec["response"]["status"] == "cancelled"
    finally:
        rv._clear_cancel(rid)


@pytest.mark.django_db(transaction=True)
def test_worker_does_not_overwrite_cancel_endpoint_status(monkeypatch):
    """Cancel API may persist cancelled while the worker is still running.

    Without a sticky-cancelled guard, the worker's terminal ``completed`` (or
    progress ``in_progress``) write would resurrect the job — a false-success
    cancel for pollers that already saw ``cancelled``.
    """
    rid = "resp_cancel_race1"
    _save_state(rid, "in_progress")

    async def _slow_then_done(bp, messages, cancel_check=None, on_progress=None, user_id=None):
        # Simulate cancel landing mid-flight after the last cancel_check.
        _save_state(rid, "cancelled", with_task=False)
        return "should-not-persist", None

    monkeypatch.setattr(rv, "_consume_blueprint", _slow_then_done)
    # Do not pre-set the cancel flag — this is the store-status race only.
    rv._run_background_response(
        rid, "cancel_race", "chatbot", [{"role": "user", "content": "x"}], None, None
    )
    rec = responses_store.load(rid)
    assert rec is not None
    assert rec["response"]["status"] == "cancelled"
    assert "should-not-persist" not in (rec["response"].get("output_text") or "")


# --- restart resume --------------------------------------------------------- #

@pytest.mark.django_db(transaction=True)
def test_resume_pending_reruns_interrupted_task():
    rid = "resp_resume1"
    _save_state(rid, "in_progress")  # as if a restart left it mid-flight
    resumed = rv.resume_pending_responses()
    assert resumed == 1
    # The resumed worker runs chatbot and reaches a terminal state.
    for _ in range(50):
        rec = responses_store.load(rid)
        if rec and rec["response"]["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.1)
    assert responses_store.load(rid)["response"]["status"] == "completed"


@pytest.mark.django_db(transaction=True)
def test_resume_ignores_terminal_tasks():
    _save_state("resp_term1", "completed", with_task=False)
    assert rv.resume_pending_responses() == 0


# --- no-auth opt-out -------------------------------------------------------- #

def test_no_auth_opt_out(monkeypatch):
    from swarm.utils import env_utils

    monkeypatch.setattr(env_utils, "_api_auth_disabled_warning_emitted", False)
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("SWARM_API_KEY", raising=False)
    monkeypatch.setenv("DJANGO_DEBUG", "false")

    # Production + no token + no opt-out -> refuses (ImproperlyConfigured).
    from django.core.exceptions import ImproperlyConfigured
    monkeypatch.delenv("SWARM_ALLOW_NO_AUTH", raising=False)
    with pytest.raises(ImproperlyConfigured):
        env_utils.get_enforced_api_auth_token()

    # Production + no token + explicit opt-out -> permitted (None), warns.
    monkeypatch.setattr(env_utils, "_api_auth_disabled_warning_emitted", False)
    monkeypatch.setenv("SWARM_ALLOW_NO_AUTH", "true")
    assert env_utils.get_enforced_api_auth_token() is None
