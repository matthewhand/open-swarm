"""GET /v1/system/ — local store facts for Settings System (REQ-56)."""

from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from swarm.models import ChatConversation, ChatMessage


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_system_local_store_empty(api_client):
    response = api_client.get("/v1/system/")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["conversation_count"] == 0
    assert body["message_count"] == 0
    assert isinstance(body["size_bytes"], int)
    assert isinstance(body["size_label"], str)
    assert isinstance(body["path"], str)
    blob = str(body).lower()
    assert "django" not in blob
    assert "django.db" not in blob
    assert "backends.sqlite" not in blob
    assert "orm" not in blob
    assert "://" not in body["path"]
    assert "password" not in blob


@pytest.mark.django_db
def test_system_local_store_counts(api_client, test_user):
    conv = ChatConversation.objects.create(conversation_id="sys-1", student=test_user)
    ChatMessage.objects.create(conversation=conv, sender="user", content="hello")
    ChatMessage.objects.create(conversation=conv, sender="assistant", content="hi")
    other = ChatConversation.objects.create(conversation_id="sys-2", student=test_user)
    ChatMessage.objects.create(conversation=other, sender="user", content="again")

    response = api_client.get("/v1/system")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["conversation_count"] == 2
    assert body["message_count"] == 3
    assert isinstance(body["size_bytes"], int)
    assert isinstance(body["size_label"], str)
    assert "://" not in body["path"]
    assert "hunter2" not in body["path"]
