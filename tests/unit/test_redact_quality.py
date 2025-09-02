import copy
from swarm.utils.redact import redact_sensitive_data


def test_redact_does_not_mutate_input():
    original = {
        "api_key": "sk-live-xyz",
        "nested": {"password": "p@ss"},
        "list": [{"token": "t1"}, {"ok": "v"}],
    }
    snapshot = copy.deepcopy(original)

    _ = redact_sensitive_data(original)

    # Ensure the original structure and values remain unchanged
    assert original == snapshot, "Function should not mutate input structures"


def test_redact_custom_sensitive_keys_override_defaults():
    data = {
        "username": "alice",
        "note": "public",
        "token": "tkn-should-stay",
    }
    # Only redact keys we specify; default keys should not apply when custom provided
    redacted = redact_sensitive_data(data, sensitive_keys=["username"]) 
    assert redacted["username"] == "[REDACTED]"
    # Defaults like 'token' should not be redacted when custom list is supplied
    assert redacted["token"] == "tkn-should-stay"
    assert redacted["note"] == "public"

