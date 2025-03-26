import pytest
# Import from correct location
from src.swarm.utils.message_utils import filter_messages
# Import the serializer used in the test data
from src.swarm.utils.general_utils import serialize_datetime
import datetime # Import datetime for creating test data

def test_filter_messages_empty_and_none_content():
    messages = [
        {"role": "system", "content": "System message"}, # Keep
        {"role": "user", "content": ""}, # Empty string content -> should filter out
        {"role": "assistant", "content": None}, # None content -> should filter out
        {"role": "user", "content": "Valid message"}, # Keep
        {"role": "assistant", "tool_calls": [{"id": "1", "type":"function", "function": {"name": "foo"}}]}, # No content, but has tool calls -> Keep
        {"role": "assistant", "content": "  "}, # Whitespace only content -> should filter out
        {"role": "user"}, # No content key -> should filter out
    ]
    filtered = filter_messages(messages)
    # Expected: Keep messages with non-empty/non-whitespace content OR non-empty tool_calls
    # System message (content)
    # Valid message (content)
    # Assistant message (tool_calls)
    assert len(filtered) == 3, f"Expected 3 messages, got {len(filtered)}: {filtered}"
    assert filtered[0]["content"] == "System message"
    assert filtered[1]["content"] == "Valid message"
    assert "tool_calls" in filtered[2] and filtered[2].get("content") is None

def test_filter_messages_all_valid():
    messages = [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "User"},
        {"role": "assistant", "content": "Assistant", "tool_calls": []} # Content present, empty tool_calls is fine -> Keep
    ]
    filtered = filter_messages(messages)
    assert len(filtered) == 3
    assert filtered == messages

def test_filter_messages_with_non_dict_items():
    messages = [
        {"role": "system", "content": "Valid"},
        "a string message", # Invalid item
        None, # Invalid item
        {"role": "user", "content": "Another valid"},
    ]
    filtered = filter_messages(messages)
    # Expect only the valid dictionaries to remain
    assert len(filtered) == 2
    assert filtered[0]["content"] == "Valid"
    assert filtered[1]["content"] == "Another valid"

def test_filter_messages_empty_input():
    messages = []
    filtered = filter_messages(messages)
    assert len(filtered) == 0
    assert filtered == []

# Test interaction with other keys
def test_filter_messages_ignores_other_keys():
     timestamp = datetime.datetime.now()
     messages = [
         {"role": "system", "content": "System", "timestamp": serialize_datetime(timestamp)}, # Keep
         {"role": "user", "content": ""}, # Filter out
         {"role": "assistant", "content": None, "timestamp": serialize_datetime(timestamp)}, # Filter out
     ]
     filtered = filter_messages(messages)
     assert len(filtered) == 1
     assert filtered[0]["content"] == "System"
     # Ensure the extra key was preserved
     assert "timestamp" in filtered[0]
     assert filtered[0]["timestamp"] == timestamp.isoformat()
