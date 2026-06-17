"""Tests for the OpenAI Responses API endpoint (`/v1/responses`).

The ``chatbot`` blueprint returns deterministic, network-free output under
``SWARM_TEST_MODE`` (``"You said: <text>"``), so these tests need no model /
API key. ``validate_model_access`` is patched to True (it normally requires the
blueprint to appear in discovery, which it does, but patching keeps the test
isolated from discovery state).
"""
import json
import os

import pytest
from django.urls import reverse
from rest_framework import status

# Ensure deterministic blueprint output regardless of how the suite is launched.
os.environ.setdefault("SWARM_TEST_MODE", "1")


@pytest.mark.django_db(transaction=True)
class TestResponsesAPI:

    @pytest.fixture(autouse=True)
    def _enable_test_mode(self, monkeypatch):
        monkeypatch.setenv("SWARM_TEST_MODE", "1")
        # Keep the test independent of blueprint-discovery state.
        monkeypatch.setattr("swarm.views.responses_views.validate_model_access", lambda *a, **k: True)

    @pytest.mark.asyncio
    async def test_responses_string_input(self, async_client):
        url = reverse("responses")
        data = {"model": "chatbot", "input": "ping"}
        response = await async_client.post(
            url, data=json.dumps(data), content_type="application/json", SERVER_NAME="localhost"
        )

        assert response.status_code == status.HTTP_200_OK
        body = json.loads(response.content)
        assert body["object"] == "response"
        assert body["status"] == "completed"
        assert body["model"] == "chatbot"
        assert body["output_text"]
        assert "ping" in body["output_text"]
        # Output item structure.
        assert body["output"][0]["type"] == "message"
        assert body["output"][0]["content"][0]["type"] == "output_text"
        assert body["output"][0]["content"][0]["text"] == body["output_text"]

    @pytest.mark.asyncio
    async def test_responses_array_input_with_instructions(self, async_client):
        url = reverse("responses")
        data = {
            "model": "chatbot",
            "instructions": "Be terse.",
            "input": [{"role": "user", "content": "hello there"}],
        }
        response = await async_client.post(
            url, data=json.dumps(data), content_type="application/json", SERVER_NAME="localhost"
        )

        assert response.status_code == status.HTTP_200_OK
        body = json.loads(response.content)
        assert body["object"] == "response"
        assert "hello there" in body["output_text"]

    @pytest.mark.asyncio
    async def test_responses_missing_input_is_400(self, async_client):
        url = reverse("responses")
        data = {"model": "chatbot"}
        response = await async_client.post(
            url, data=json.dumps(data), content_type="application/json", SERVER_NAME="localhost"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_responses_unknown_model_is_404(self, async_client, monkeypatch):
        # For unknown-model behavior, don't short-circuit access validation.
        monkeypatch.setattr(
            "swarm.views.responses_views.validate_model_access", lambda *a, **k: False
        )
        url = reverse("responses")
        data = {"model": "does-not-exist", "input": "ping"}
        response = await async_client.post(
            url, data=json.dumps(data), content_type="application/json", SERVER_NAME="localhost"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db(transaction=True)
class TestResponsesStateful:
    """Statefulness: store, retrieve, chain via previous_response_id, delete."""

    @pytest.fixture(autouse=True)
    def _enable_test_mode(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SWARM_TEST_MODE", "1")
        # Isolate the on-disk response store to a per-test tmp dir.
        monkeypatch.setenv("SWARM_RESPONSES_DIR", str(tmp_path))
        monkeypatch.setattr("swarm.views.responses_views.validate_model_access", lambda *a, **k: True)

    async def _create(self, async_client, data):
        url = reverse("responses")
        return await async_client.post(
            url, data=json.dumps(data), content_type="application/json", SERVER_NAME="localhost"
        )

    @pytest.mark.asyncio
    async def test_response_is_stored_and_retrievable(self, async_client):
        resp = await self._create(async_client, {"model": "chatbot", "input": "ping"})
        assert resp.status_code == status.HTTP_200_OK
        rid = json.loads(resp.content)["id"]

        get_url = reverse("responses-detail", kwargs={"response_id": rid})
        got = await async_client.get(get_url, SERVER_NAME="localhost")
        assert got.status_code == status.HTTP_200_OK
        body = json.loads(got.content)
        assert body["id"] == rid
        assert body["object"] == "response"

    @pytest.mark.asyncio
    async def test_previous_response_id_chains_context(self, async_client):
        first = await self._create(async_client, {"model": "chatbot", "input": "my name is Ada"})
        first_id = json.loads(first.content)["id"]

        second = await self._create(
            async_client,
            {"model": "chatbot", "input": "again", "previous_response_id": first_id},
        )
        assert second.status_code == status.HTTP_200_OK
        body = json.loads(second.content)
        assert body["previous_response_id"] == first_id
        assert body["id"] != first_id

        # The chained request must replay the prior transcript: the stored record
        # for the second response contains the first turn's user + assistant
        # messages ahead of the new turn.
        from swarm.core import responses_store

        record = responses_store.load(body["id"])
        assert record is not None
        contents = [m.get("content") for m in record["messages"]]
        assert "my name is Ada" in contents  # replayed prior user message
        assert "again" in contents           # the new turn

    @pytest.mark.asyncio
    async def test_unknown_previous_response_id_is_404(self, async_client):
        resp = await self._create(
            async_client,
            {"model": "chatbot", "input": "hi", "previous_response_id": "resp_doesnotexist"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_store_false_is_not_persisted(self, async_client):
        resp = await self._create(async_client, {"model": "chatbot", "input": "ping", "store": False})
        assert resp.status_code == status.HTTP_200_OK
        rid = json.loads(resp.content)["id"]

        get_url = reverse("responses-detail", kwargs={"response_id": rid})
        got = await async_client.get(get_url, SERVER_NAME="localhost")
        assert got.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_response(self, async_client):
        resp = await self._create(async_client, {"model": "chatbot", "input": "ping"})
        rid = json.loads(resp.content)["id"]
        detail_url = reverse("responses-detail", kwargs={"response_id": rid})

        deleted = await async_client.delete(detail_url, SERVER_NAME="localhost")
        assert deleted.status_code == status.HTTP_200_OK
        body = json.loads(deleted.content)
        assert body["id"] == rid
        assert body["object"] == "response.deleted"
        assert body["deleted"] is True

        # Gone afterwards.
        got = await async_client.get(detail_url, SERVER_NAME="localhost")
        assert got.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_unknown_response_is_404(self, async_client):
        get_url = reverse("responses-detail", kwargs={"response_id": "resp_missing"})
        got = await async_client.get(get_url, SERVER_NAME="localhost")
        assert got.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_responses_reports_nonzero_token_usage(client):
    resp = client.post(
        "/v1/responses",
        data='{"model": "cli_fusion", "input": "In one word, capital of France?"}',
        content_type="application/json",
    )
    assert resp.status_code == 200
    usage = resp.json()["usage"]
    assert usage["input_tokens"] > 0
    assert usage["output_tokens"] > 0
    assert usage["total_tokens"] == usage["input_tokens"] + usage["output_tokens"]
