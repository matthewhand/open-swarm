from swarm.utils.redact import redact_sensitive_data


def test_redact_sensitive_data_case_insensitive_keys():
    data = {
        "API_KEY": "AAA-BBB-CCC",
        "Password": "letmein",
        "ToKeN": "xyz",
        "nested": {"Client_Secret": "shh"},
        "ok": "value",
    }
    redacted = redact_sensitive_data(data)
    assert redacted["API_KEY"] == "[REDACTED]"
    assert redacted["Password"] == "[REDACTED]"
    assert redacted["ToKeN"] == "[REDACTED]"
    assert redacted["nested"]["Client_Secret"] == "[REDACTED]"
    assert redacted["ok"] == "value"


def test_redact_sensitive_data_custom_mask_overrides_reveal_chars():
    data = {"api_key": "sk-1234567890"}
    # When a custom mask is provided, it should be used verbatim
    redacted = redact_sensitive_data(data, reveal_chars=4, mask="***MASK***")
    assert redacted["api_key"] == "***MASK***"


def test_redact_sensitive_data_deeply_nested_lists_and_dicts():
    data = {
        "users": [
            {"name": "A", "credentials": {"password": "p@ss"}},
            [
                {"token": "t1"},
                {"misc": [{"api_key": "k1"}, {"note": "safe"}]},
            ],
        ],
        "meta": {"count": 2},
    }
    out = redact_sensitive_data(data)
    # First user password masked
    assert out["users"][0]["credentials"]["password"] == "[REDACTED]"
    # Nested list token masked
    assert out["users"][1][0]["token"] == "[REDACTED]"
    # Deep list inside dict masked for api_key, preserves non-sensitive
    assert out["users"][1][1]["misc"][0]["api_key"] == "[REDACTED]"
    assert out["users"][1][1]["misc"][1]["note"] == "safe"
    # Unrelated metadata preserved
    assert out["meta"]["count"] == 2

