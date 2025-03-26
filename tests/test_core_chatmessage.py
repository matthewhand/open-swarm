import pytest  # type: ignore
import json
from swarm.core import ChatMessage

def test_model_dump_json_removes_empty_tool_calls():
    msg = ChatMessage(role="assistant", content="Test message", tool_calls=[])
    dumped = json.loads(msg.model_dump_json())
    assert "tool_calls" not in dumped or dumped["tool_calls"] == []

def test_model_dump_json_preserves_tool_calls():
    tool_calls_data = [{"id": "123", "type": "function", "function": {"name": "dummy", "arguments": "{}"}}]
    msg = ChatMessage(role="assistant", content="Another test", tool_calls=tool_calls_data)
    dumped = msg.model_dump_json()
    assert "tool_calls" in dumped
    assert "dummy" in dumped
