import pytest
from unittest.mock import patch
# Import only the function, not internal variables
from swarm.utils.redact import redact_sensitive_data

# Define the default keys within the test module for comparison if needed
TEST_DEFAULT_SENSITIVE_KEYS = ["secret", "password", "api_key", "apikey", "token", "access_token", "client_secret"]

# Test cases for the redact_sensitive_data function

def test_redact_sensitive_key_in_dict():
    """Test redacting a default sensitive key ('api_key')."""
    data = {"api_key": "secretvalue123", "other": "value"}
    result_full = redact_sensitive_data(data, reveal_chars=0) # Use default mask "[REDACTED]"
    assert result_full["api_key"] == "[REDACTED]"
    assert result_full["other"] == "value"
    result_partial = redact_sensitive_data(data, reveal_chars=3, mask="***")
    expected_partial = "sec***123"
    assert result_partial["api_key"] == expected_partial
    assert result_partial["other"] == "value"

def test_no_redaction_for_non_sensitive_key():
    """Test that non-sensitive keys are not redacted."""
    data = {"username": "normal_user", "info": "some data"}
    result = redact_sensitive_data(data, reveal_chars=3, mask="***")
    assert result["username"] == "normal_user"
    assert result["info"] == "some data"

def test_redact_in_nested_structure():
    """Test redaction within nested dictionaries and lists."""
    data = {
        "level1": {"token": "secrettokenvalue", "info": "data"},
        "list": [{"password": "secretpass123"}, "nochange", {"other_key": "value"}],
        "apikey": "anothersecretkey"
    }
    result = redact_sensitive_data(data, reveal_chars=2, mask="--")
    assert result["level1"]["token"] == "se--ue"
    assert result["list"][0]["password"] == "se--23"
    assert result["apikey"] == "an--ey"
    assert result["level1"]["info"] == "data"
    assert result["list"][1] == "nochange" # Standalone string in list is NOT redacted
    assert result["list"][2]["other_key"] == "value"

# This test passes, keep it enabled
def test_list_input():
    """Test redaction when the top-level input is a list. Standalone strings should NOT be redacted."""
    data = ["justastring", "secretvalue", {"api_key": "mykey123"}]
    result = redact_sensitive_data(data, reveal_chars=2, mask="xx")
    # Corrected Assertion: Standalone strings are not redacted
    assert result[0] == "justastring"
    assert result[1] == "secretvalue"
    # Nested dictionary IS redacted
    assert isinstance(result[2], dict)
    assert result[2]["api_key"] == "myxx23"

def test_short_string():
    """Test redaction of strings shorter than or equal to 2*reveal_chars."""
    data = {"api_key": "short"}
    # Test full redaction (reveal_chars=0)
    result_full = redact_sensitive_data(data, reveal_chars=0, mask="[REDACTED]")
    assert result_full["api_key"] == "[REDACTED]"
    # Test partial redaction where string is too short
    result_partial = redact_sensitive_data(data, reveal_chars=3, mask="***")
    assert result_partial["api_key"] == "***" # Uses mask directly
    data_exact = {"token": "secret"}
    result_exact = redact_sensitive_data(data_exact, reveal_chars=3, mask="***")
    assert result_exact["token"] == "***" # Uses mask directly
    data_long_enough = {"password": "secret1"}
    result_long = redact_sensitive_data(data_long_enough, reveal_chars=3, mask="***")
    assert result_long["password"] == "sec***et1" # Partial redaction applies

def test_custom_sensitive_keys():
    """Test using a custom list of sensitive keys."""
    data = {"user_id": "usr_123", "session_key": "sess_abc", "api_key": "api_def"}
    custom_keys = ["session_key", "user_id"]
    result = redact_sensitive_data(data, sensitive_keys=custom_keys, reveal_chars=0)
    assert result["user_id"] == "[REDACTED]"
    assert result["session_key"] == "[REDACTED]"
    assert result["api_key"] == "api_def" # Default key, but not in custom list

def test_different_mask_and_reveal():
    """Test using different mask and reveal_chars values."""
    data = {"token": "verylongtokenvalue"}
    result = redact_sensitive_data(data, reveal_chars=4, mask="...")
    assert result["token"] == "very...alue"
    result_zero_reveal = redact_sensitive_data(data, reveal_chars=0, mask="[HIDDEN]")
    assert result_zero_reveal["token"] == "[HIDDEN]" # Should use the mask directly

def test_non_string_sensitive_value():
     """Test redacting non-string values associated with sensitive keys."""
     data = {"api_key": 123456789, "other": ["list", "items"]}
     result = redact_sensitive_data(data, reveal_chars=2, mask="--")
     assert result["api_key"] == "[REDACTED NON-STRING]" # Check specific placeholder
     assert result["other"] == ["list", "items"]

def test_empty_dict_list():
     """Test with empty dictionaries and lists."""
     assert redact_sensitive_data({}) == {}
     assert redact_sensitive_data([]) == []
     data = {"empty_list": [], "nested": {"empty_dict": {}, "api_key": "key"}}
     result = redact_sensitive_data(data) # Uses default mask "[REDACTED]"
     assert result["empty_list"] == []
     assert result["nested"]["empty_dict"] == {}
     assert result["nested"]["api_key"] == "[REDACTED]" # Check against default mask
