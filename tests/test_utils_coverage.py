import pytest
from unittest.mock import patch, MagicMock
import json
import os
from typing import List, Dict, Any

# Test target functions
try:
    from swarm.extensions.blueprint.message_utils import truncate_preserve_pairs
    from swarm.utils.context_utils import get_token_count
    from swarm.utils.general_utils import extract_chat_id
    UTILS_AVAILABLE = True
except ImportError as e:
    UTILS_AVAILABLE = False
    pytest.skip(f"Skipping util coverage tests: Import failed - {e}", allow_module_level=True)


# --- Test Data ---

# Data for get_token_count
@pytest.mark.parametrize("text, model, expected_count", [
    ("Hello world", "gpt-4", 2),
    ("你好世界", "gpt-4", 2),
    ("", "gpt-4", 0),
    ("  ", "gpt-4", 2),
])
@patch('tiktoken.encoding_for_model')
def test_get_token_count_basic(mock_encoding_for_model, text, model, expected_count):
    mock_encoder = MagicMock()
    mock_encoder.encode.return_value = list(range(expected_count))
    mock_encoding_for_model.return_value = mock_encoder

    assert get_token_count(text, model) == expected_count

    processed_text = ""
    if isinstance(text, str): processed_text = text
    elif text is not None:
        try: processed_text = json.dumps(text, separators=(',', ':'))
        except TypeError: processed_text = str(text)

    if processed_text:
        try:
            import tiktoken
            tiktoken_available = True
        except ImportError: tiktoken_available = False

        if tiktoken_available:
            mock_encoding_for_model.assert_called_once_with(model)
            mock_encoder.encode.assert_called_once_with(processed_text)
        else:
             assert not mock_encoding_for_model.called
             assert not mock_encoder.encode.called
    else:
        assert not mock_encoding_for_model.called
        assert not mock_encoder.encode.called

@patch('tiktoken.encoding_for_model')
def test_get_token_count_empty(mock_encoding_for_model):
    assert get_token_count("", "gpt-4") == 0
    assert not mock_encoding_for_model.called

# Data for truncate_preserve_pairs
def mock_get_token_count_logic(text, model):
    try:
        if isinstance(text, str) and text.strip().startswith('{'):
             msg_dict = json.loads(text)
             return len(msg_dict.get("content", "") or "")
        elif isinstance(text, dict):
             return len(text.get("content", "") or "")
        else: return 0
    except json.JSONDecodeError: return 0

@patch('swarm.extensions.blueprint.message_utils.get_token_count', mock_get_token_count_logic)
def test_truncate_preserve_pairs_basic():
    messages = [ {"role": "system", "content": "S"}, {"role": "user", "content": "U1"}, {"role": "assistant", "content": "A1"}, {"role": "user", "content": "U2"}, {"role": "assistant", "content": None, "tool_calls": [{"id": "t1"}]}, {"role": "tool", "tool_call_id": "t1", "content": "T1R"}, {"role": "assistant", "content": "A2"}, ]
    max_tokens = 10; max_messages = 5
    expected = [ {"role": "system", "content": "S"}, {"role": "user", "content": "U2"}, {"role": "assistant", "content": None, "tool_calls": [{"id": "t1"}]}, {"role": "tool", "tool_call_id": "t1", "content": "T1R"}, {"role": "assistant", "content": "A2"}, ]
    result = truncate_preserve_pairs(messages, "test-model", max_tokens, max_messages)
    result_simplified = [{"role": m.get("role"), "content": m.get("content"), "tool_calls": m.get("tool_calls"), "tool_call_id": m.get("tool_call_id")} for m in result]
    expected_simplified = [{"role": m.get("role"), "content": m.get("content"), "tool_calls": m.get("tool_calls"), "tool_call_id": m.get("tool_call_id")} for m in expected]
    assert result_simplified == expected_simplified, f"Expected: {json.dumps(expected_simplified, indent=2)}\nGot: {json.dumps(result_simplified, indent=2)}"


# Data for extract_chat_id - Updated expectations for json_parse path
@pytest.mark.parametrize(
    "payload, path_to_set, expected_id",
    [
        ({"metadata": {"channelInfo": {"channelId": "C123"}}}, "metadata.channelInfo.channelId", "C123"),
        # Expect this to work now due to manual handling in extract_chat_id
        ({"messages": [{"tool_calls": [{"function": {"arguments": '{"chat_id":"T456"}'}}]}]}, "`json_parse(messages[-1].tool_calls[-1].function.arguments).chat_id`", "T456"),
        ({"metadata": {"userInfo": {"userId": "U789"}}}, "metadata.userInfo.userId", "U789"),
        ({"metadata": {"channelInfo": {"channelId": None}}}, "metadata.channelInfo.channelId", ""),
        ({"metadata": {"channelInfo": {}}}, "metadata.channelInfo.channelId", ""),
        ({"metadata": {"invalid-key": "V001"}}, "metadata.invalid-key", ""),
        # Expect this to fail parsing inside extract_chat_id and return ""
        ({"messages": [{"tool_calls": [{"function": {"arguments": 'invalid json'}}]}]}, "`json_parse(messages[-1].tool_calls[-1].function.arguments).chat_id`", ""),
        ({"metadata": {"chat_details": "D007"}}, "metadata.chat_details", "D007"),
        ({}, "metadata.channelInfo.channelId", ""),
    ],
    ids=["channelId", "toolArgsJson", "userId", "channelIdNull", "channelIdMissing", "invalidJmesPathKey", "invalidToolArgsJson", "customPath", "emptyPayload"]
)
def test_extract_chat_id(payload: Dict, path_to_set: str, expected_id: str, monkeypatch):
    """Test chat ID extraction using default and custom paths by setting ENV."""
    # Check if the path is one of the defaults *excluding* the json_parse one for the default check
    default_paths_for_check = [
        "metadata.channelInfo.channelId",
        "metadata.userInfo.userId"
    ]
    # The json_parse path in DEFAULT_CHAT_ID_PATHS_LIST requires special handling check
    json_parse_path = "`json_parse(messages[-1].tool_calls[-1].function.arguments).chat_id`"

    if path_to_set in default_paths_for_check or path_to_set == json_parse_path:
         # Test default behavior by unsetting env var
         monkeypatch.delenv("STATEFUL_CHAT_ID_PATH", raising=False)
         assert extract_chat_id(payload) == expected_id, f"Failed with default paths for: {path_to_set}"
    elif path_to_set == "metadata.chat_details":
         # Test custom path explicitly
         monkeypatch.setenv("STATEFUL_CHAT_ID_PATH", path_to_set)
         assert extract_chat_id(payload) == expected_id, f"Failed with custom path: {path_to_set}"
    else:
         # Test invalid/other paths expect ""
         monkeypatch.setenv("STATEFUL_CHAT_ID_PATH", path_to_set)
         assert extract_chat_id(payload) == expected_id, f"Failed with specific path: {path_to_set}"

def test_extract_chat_id_no_env_var(monkeypatch):
    """Test that extract_chat_id uses defaults when env var is not set."""
    monkeypatch.delenv("STATEFUL_CHAT_ID_PATH", raising=False)
    payload = {"metadata": {"channelInfo": {"channelId": "CDefault"}}}
    assert extract_chat_id(payload) == "CDefault"

