
import logging
from swarm.utils.message_sequence import validate_message_sequence, repair_message_payload

def test_validate_message_sequence_with_non_dict():
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        "not a dict",
        {"role": "user", "content": "Hello!"},
        None,
        {"role": "assistant", "content": "Hi there!", "tool_calls": [{"id": "call_123", "type": "function", "function": {"name": "get_weather", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "call_123", "content": "It is sunny."},
        123
    ]

    validated = validate_message_sequence(messages)

    assert len(validated) == 4
    assert validated[0]["role"] == "system"
    assert validated[1]["role"] == "user"
    assert validated[2]["role"] == "assistant"
    assert validated[3]["role"] == "tool"
    assert all(isinstance(m, dict) for m in validated)

def test_validate_message_sequence_orphan_tool():
    messages = [
        {"role": "user", "content": "What is the weather?"},
        {"role": "tool", "tool_call_id": "call_999", "content": "It is raining."},
    ]
    validated = validate_message_sequence(messages)
    assert len(validated) == 1
    assert validated[0]["role"] == "user"

def test_repair_message_payload_missing_tool_response():
    messages = [
        {"role": "user", "content": "Call tool"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "test_tool", "arguments": "{}"}}]},
    ]
    repaired = repair_message_payload(messages)
    assert len(repaired) == 3
    assert repaired[0]["role"] == "user"
    assert repaired[1]["role"] == "assistant"
    assert repaired[2]["role"] == "tool"
    assert repaired[2]["tool_call_id"] == "call_1"
    assert "Error" in repaired[2]["content"]

def test_repair_message_payload_orphan_tool_insertion():
    messages = [
        {"role": "assistant", "content": "I will call a tool", "tool_calls": [{"id": "call_2", "type": "function", "function": {"name": "other_tool", "arguments": "{}"}}]},
        {"role": "user", "content": "Wait, also this tool response:"},
        {"role": "tool", "tool_call_id": "call_2", "content": "Result of call 2"}
    ]

    repaired = repair_message_payload(messages)

    roles = [m["role"] for m in repaired]
    assert "assistant" in roles
    assert "tool" in roles
    assert "user" in roles
    assert len(repaired) == 3
    assert repaired[1]["role"] == "tool"
    assert "Error" in repaired[1]["content"]

if __name__ == "__main__":
    test_validate_message_sequence_with_non_dict()
    test_validate_message_sequence_orphan_tool()
    test_repair_message_payload_missing_tool_response()
    test_repair_message_payload_orphan_tool_insertion()
    print("All manual tests passed!")
