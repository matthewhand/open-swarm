import pytest
import json
from typing import List, Dict, Any
from unittest.mock import patch

# Directly import
from swarm.extensions.blueprint.message_utils import (
    truncate_preserve_pairs,
    truncate_strict_token,
    truncate_recent_only,
)

# Wrapper function
def truncate_message_history(
    messages: List[Dict[str, Any]],
    model: str,
    max_tokens: int = 8000,
    max_messages: int = 50,
    mode: str = "pairs",
) -> List[Dict[str, Any]]:
    if mode == "pairs":
        return truncate_preserve_pairs(messages, model, max_tokens, max_messages)
    elif mode == "strict_token":
        return truncate_preserve_pairs(messages, model, max_tokens, max_messages)
    elif mode == "recent_only":
        return truncate_recent_only(messages, model, max_messages)
    else:
        return truncate_preserve_pairs(messages, model, max_tokens, max_messages)

# Corrected mock: Expects JSON string 'text', loads it, gets len of 'content'
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
def run_truncation_test(messages: List[Dict], max_tokens: int, max_messages: int, expected_messages: List[Dict], mode: str = "pairs"):
    """Helper function to run truncation tests with corrected mocked token count."""
    result = truncate_message_history(messages, "test-model", max_tokens, max_messages, mode=mode)
    result_simplified = [{"role": m.get("role"), "content": m.get("content"), "tool_calls": m.get("tool_calls"), "tool_call_id": m.get("tool_call_id")} for m in result]
    expected_simplified = [{"role": m.get("role"), "content": m.get("content"), "tool_calls": m.get("tool_calls"), "tool_call_id": m.get("tool_call_id")} for m in expected_messages]
    assert result_simplified == expected_simplified, \
        f"\nMode: {mode}\nMax Tokens: {max_tokens}\nMax Messages: {max_messages}\n" \
        f"Expected: {json.dumps(expected_simplified, indent=2)}\n" \
        f"Got:      {json.dumps(result_simplified, indent=2)}"

# Test Data
MESSAGES_SIMPLE = [ {"role": "system", "content": "Sys"}, {"role": "user", "content": "User1"}, {"role": "assistant", "content": "Assist1"}, ]
MESSAGES_TOOL = [ {"role": "system", "content": "Sys"}, {"role": "user", "content": "User1"}, {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "function": {"name": "toolA", "arguments": "{}"}}]}, {"role": "tool", "tool_call_id": "call_1", "content": "ToolA result"}, {"role": "assistant", "content": "Assist1 based on ToolA"}, {"role": "user", "content": "User2"}, {"role": "assistant", "content": None, "tool_calls": [{"id": "call_2", "function": {"name": "toolB", "arguments": "{}"}}]}, {"role": "tool", "tool_call_id": "call_2", "content": "ToolB result"}, {"role": "assistant", "content": "Assist2 based on ToolB"}, ]

# Test Cases
@pytest.mark.parametrize("max_tokens, max_messages", [(1000, 10), (80, 3)])
def test_truncate_no_action(max_tokens, max_messages):
    run_truncation_test(MESSAGES_SIMPLE, max_tokens, max_messages, MESSAGES_SIMPLE)

@pytest.mark.parametrize("max_messages, expected_num_non_system", [(2, 1), (1, 0)]) # Param is num non-system msgs to keep
def test_truncate_by_message_count(max_messages, expected_num_non_system):
    # Correctly calculate expected list for recent_only
    if expected_num_non_system > 0:
        expected = [MESSAGES_SIMPLE[0]] + MESSAGES_SIMPLE[-expected_num_non_system:]
    else:
        expected = [MESSAGES_SIMPLE[0]] # Only system message
    run_truncation_test(MESSAGES_SIMPLE, 1000, max_messages, expected, mode="recent_only")

@pytest.mark.parametrize("max_tokens, _unused", [(30, 0), (15, 0), (10, 0)])
def test_truncate_by_token_count(max_tokens, _unused):
    if max_tokens >= 15: expected = MESSAGES_SIMPLE
    elif max_tokens >= 10: expected = [MESSAGES_SIMPLE[0], MESSAGES_SIMPLE[2]]
    else: expected = [MESSAGES_SIMPLE[0]]
    run_truncation_test(MESSAGES_SIMPLE, max_tokens, 10, expected, mode="pairs")

def test_truncate_sophisticated_preserves_pairs():
    expected = [ MESSAGES_TOOL[0], MESSAGES_TOOL[5], MESSAGES_TOOL[6], MESSAGES_TOOL[7], MESSAGES_TOOL[8], ]
    run_truncation_test(MESSAGES_TOOL, 50, 5, expected, mode="pairs")

def test_truncate_sophisticated_preserves_pairs_complex():
    msgs_complex = MESSAGES_TOOL + [ {"role": "user", "content": "User3"}, {"role": "assistant", "content": None, "tool_calls": [{"id": "call_3", "function": {"name": "toolC", "arguments": "{}"}}]}, {"role": "tool", "tool_call_id": "call_3", "content": "ToolC result"}, {"role": "assistant", "content": "Assist3 based on ToolC"}, ]
    expected = [ msgs_complex[0], msgs_complex[9], msgs_complex[10], msgs_complex[11], msgs_complex[12], ]
    run_truncation_test(msgs_complex, 60, 7, expected, mode="pairs")

def test_truncate_sophisticated_drops_lone_tool():
    msgs_lone = [ {"role": "system", "content": "Sys"}, {"role": "user", "content": "UserVeryLong..."*10}, {"role": "assistant", "content": None, "tool_calls": [{"id": "call_early", "function": {"name": "toolEarly", "arguments": "{}"}}]}, {"role": "user", "content": "User2"}, {"role": "tool", "tool_call_id": "call_early", "content": "ToolEarly result"}, ]
    expected = [ msgs_lone[0], msgs_lone[2], msgs_lone[3], ]
    run_truncation_test(msgs_lone, 18, 3, expected, mode="pairs")
