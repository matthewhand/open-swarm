"""Unit tests for the REQ-144 preferences registry helpers."""

from django.contrib.auth import get_user_model
from django.test import RequestFactory

from swarm.core.user_preferences import (
    coerce_values,
    is_secret_key,
    merge_values,
    normalize_favourites,
    preference_identity,
    public_payload,
)

User = get_user_model()


def test_normalize_favourites_dedupes_and_fills_names():
    pins = normalize_favourites(
        ["codey", {"id": "codey", "name": "Codey"}, {"id": "stewie"}, {"id": ""}, 3]
    )
    assert pins == [
        {"id": "codey", "name": "codey"},
        {"id": "stewie", "name": "stewie"},
    ]


def test_secret_keys_are_dropped_from_the_bag():
    assert is_secret_key("api_key")
    assert is_secret_key("openai_token")
    bag = coerce_values(
        {
            "favourites": [{"id": "support"}],
            "hidden_agents": ["gate", "gate", ""],
            "theme": "dark",
            "api_key": "sk-nope",
        }
    )
    assert bag["favourites"] == [{"id": "support", "name": "support"}]
    assert bag["hidden_agents"] == ["gate"]
    assert bag["theme"] == "dark"
    assert "api_key" not in bag


def test_merge_values_patches_known_keys_only():
    current = {"favourites": [{"id": "support", "name": "Support"}], "theme": "light"}
    merged = merge_values(current, {"hidden_agents": ["skeptic"], "theme": "dark"})
    assert merged["favourites"] == [{"id": "support", "name": "Support"}]
    assert merged["hidden_agents"] == ["skeptic"]
    assert merged["theme"] == "dark"


def test_public_payload_marks_empty_and_lists_registry():
    payload = public_payload(principal="user:alice", guest=False, empty=True)
    assert payload["object"] == "user_preferences"
    assert payload["empty"] is True
    assert payload["favourites"] == []
    assert [item["key"] for item in payload["registry"]] == ["favourites", "hidden_agents"]


def test_preference_identity_uses_authenticated_user():
    factory = RequestFactory()
    request = factory.get("/v1/preferences/")
    request.user = User(username="alice")
    user, principal, guest = preference_identity(request)
    assert user is request.user
    assert principal == "user:alice"
    assert guest is False
