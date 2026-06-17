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
