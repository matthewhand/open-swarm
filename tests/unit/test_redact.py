import pytest
from swarm.utils.redact import redact_sensitive_data

def test_redact_sensitive_data_basic():
    data = {
        "api_key": "sk-1234567890abcdef",
        "password": "hunter2",
        "token": "tok-abcdef123456",
        "username": "notsecret",
        "nested": {
            "secret": "supersecret",
            "other": "value"
        },
        "list": [
            {"api_key": "sk-abcdef"},
            "nope"
        ]
    }
    redacted = redact_sensitive_data(data, reveal_chars=0)
    # API keys and tokens should be masked
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["token"] == "[REDACTED]"
    assert redacted["username"] == "notsecret"
    assert redacted["nested"]["secret"] == "[REDACTED]"
    assert redacted["nested"]["other"] == "value"
    assert redacted["list"][0]["api_key"] == "[REDACTED]"
    assert redacted["list"][1] == "nope"

def test_redact_sensitive_data_string():
    s = "my api_key is sk-123456"
    assert redact_sensitive_data(s) == s  # strings not in dict/list are not redacted

def test_redact_sensitive_data_custom_keys():
    data = {"custom_secret": "shouldhide", "foo": "bar"}
    redacted = redact_sensitive_data(data, sensitive_keys=["custom_secret"], reveal_chars=4)
    assert redacted["custom_secret"].startswith("shou") and redacted["custom_secret"].endswith("hide")
    assert "[REDACTED]" in redacted["custom_secret"]
    assert redacted["foo"] == "bar"
