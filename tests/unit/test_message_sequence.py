"""
Tests for message_sequence validation and repair utilities.

Combined coverage absorbed from the fix-message-sequence-roles and
fix-dict-messages-filtering branches (the latter's reload/sys.modules
test style was rewritten to plain function calls).
"""

from swarm.utils.message_sequence import (
    repair_message_payload,
    validate_message_sequence,
)


class TestValidateMessageSequence:
    """Test validation of message sequences."""

    def test_validate_essential_roles(self):
        """System, user, and assistant roles are preserved."""
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        result = validate_message_sequence(messages)
        assert result == messages

    def test_validate_developer_role(self):
        """Developer role is preserved (required for modern models)."""
        messages = [
            {"role": "developer", "content": "Developer instructions"},
            {"role": "user", "content": "Hello"},
        ]
        result = validate_message_sequence(messages)
        assert any(msg.get("role") == "developer" for msg in result), "Developer role should be preserved"
        assert result == messages

    def test_validate_tool_messages(self):
        """Valid tool messages are kept and orphan ones are removed."""
        messages = [
            {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "test_tool", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "call_1", "content": "success"},
            {"role": "tool", "tool_call_id": "call_orphan", "content": "should be removed"},
        ]
        result = validate_message_sequence(messages)
        assert len(result) == 2
        assert result[0]["role"] == "assistant"
        assert result[1]["role"] == "tool"
        assert result[1]["tool_call_id"] == "call_1"

    def test_validate_unknown_role(self):
        """Messages with unknown roles are removed."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "unknown", "content": "Who am I?"},
        ]
        result = validate_message_sequence(messages)
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_validate_non_dict_items(self):
        """Non-dictionary items are removed."""
        messages = [
            {"role": "user", "content": "Hello"},
            "Not a dict",
            None,
            123,
            {"role": "assistant", "content": "Hi"},
        ]
        result = validate_message_sequence(messages)
        assert len(result) == 2
        assert all(isinstance(msg, dict) for msg in result)

    def test_validate_non_list_input(self):
        """Non-list input returns an empty list."""
        assert validate_message_sequence("not a list") == []
        assert validate_message_sequence(None) == []


class TestRepairMessagePayload:
    """Test repair of message payloads."""

    def test_repair_filters_non_dict_items(self):
        """Non-dictionary items are filtered out before repair."""
        messages = [
            {"role": "system", "content": "test"},
            "NOT_A_DICT",
            {"role": "user", "content": "hi"},
            None,
            123,
            {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "test_tool", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "call_1", "content": "result"},
        ]
        repaired = repair_message_payload(messages)
        assert len(repaired) == 4
        assert all(isinstance(m, dict) for m in repaired)

    def test_repair_inserts_dummy_tool_response(self):
        """A dummy tool response is inserted for unanswered tool calls."""
        messages = [
            {"role": "assistant", "content": None, "tool_calls": [{"id": "call_missing", "type": "function", "function": {"name": "lost_tool", "arguments": "{}"}}]},
        ]
        repaired = repair_message_payload(messages)
        assert len(repaired) == 2
        assert repaired[1]["role"] == "tool"
        assert repaired[1]["tool_call_id"] == "call_missing"

    def test_repair_non_list_input(self):
        """Non-list input returns an empty list."""
        assert repair_message_payload({"role": "user"}) == []
