from swarm.utils.redact import redact_sensitive_data


def test_redacts_api_keys_and_tokens():
    data = {
        "api_key": "sk-1234567890abcdef",
        "token": "tok-abcdef123456",
        "client_secret": "secretvalue",
        "nested": {
            "password": "hunter2",
            "not_secret": "hello"
        },
        "list": [
            {"access_token": "acc-1234"},
            "not_a_secret",
            {"irrelevant": "value"}
        ]
    }
    redacted = redact_sensitive_data(data)
    # Check top-level keys
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["token"] == "[REDACTED]"
    assert redacted["client_secret"] == "[REDACTED]"
    # Check nested dict
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["nested"]["not_secret"] == "hello"
    # Check list of dicts
    assert redacted["list"][0]["access_token"] == "[REDACTED]"
    assert redacted["list"][1] == "not_a_secret"
    assert redacted["list"][2]["irrelevant"] == "value"

def test_does_not_redact_non_sensitive_strings():
    data = "this is not sensitive"
    assert redact_sensitive_data(data) == data

def test_partial_redaction_behavior():
    # Custom mask and reveal_chars
    data = {"api_key": "sk-abcdefg"}
    redacted = redact_sensitive_data(data, reveal_chars=2, mask="***")
    assert redacted["api_key"] == "***"

def test_handles_empty_and_non_dict_inputs():
    assert redact_sensitive_data({}) == {}
    assert redact_sensitive_data([]) == []
    assert redact_sensitive_data(None) is None
