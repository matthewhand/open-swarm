import pytest
# Import from the correct location
from src.swarm.utils.message_utils import filter_duplicate_system_messages

def test_filter_duplicate_system_messages():
    messages = [
        {"role": "system", "content": "First system message"},
        {"role": "user", "content": "User message"},
        {"role": "system", "content": "Second system message"}, # Should be removed
        {"role": "assistant", "content": "Assistant message"},
        {"role": "system", "content": "Third system message"}, # Should be removed
    ]
    filtered = filter_duplicate_system_messages(messages)
    assert len(filtered) == 3
    assert filtered[0]["role"] == "system"
    assert filtered[0]["content"] == "First system message"
    assert filtered[1]["role"] == "user"
    assert filtered[2]["role"] == "assistant"
    # Verify no other system messages remain
    assert len([msg for msg in filtered if isinstance(msg, dict) and msg.get("role") == "system"]) == 1

def test_filter_no_system_messages():
    messages = [
        {"role": "user", "content": "User message"},
        {"role": "assistant", "content": "Assistant message"},
    ]
    filtered = filter_duplicate_system_messages(messages)
    assert len(filtered) == 2
    # Ensure the list is identical
    assert filtered == messages

def test_filter_only_system_messages():
    messages = [
        {"role": "system", "content": "First"},
        {"role": "system", "content": "Second"},
        {"role": "system", "content": "Third"},
    ]
    filtered = filter_duplicate_system_messages(messages)
    # Should keep only the first system message
    assert len(filtered) == 1
    assert filtered[0]["role"] == "system"
    assert filtered[0]["content"] == "First"

def test_filter_empty_list():
    messages = []
    filtered = filter_duplicate_system_messages(messages)
    assert len(filtered) == 0
    assert filtered == []

def test_filter_mixed_valid_invalid():
     messages = [
         {"role": "system", "content": "Valid System"},
         "invalid string", # Should be ignored
         {"role": "user", "content": "User"},
         None, # Should be ignored
         {"role": "system", "content": "Duplicate System"}, # Should be removed
         {"not_a_role": "value"}, # Should be kept if function allows dicts without role
         123 # Should be ignored
     ]
     # Function should now handle non-dict items gracefully
     filtered = filter_duplicate_system_messages(messages)
     expected = [
         {"role": "system", "content": "Valid System"},
         # "invalid string" # Skipped
         {"role": "user", "content": "User"},
         # None # Skipped
         # {"role": "system", "content": "Duplicate System"} # Skipped (duplicate)
         {"not_a_role": "value"}, # Kept (assuming it passes if dict)
         # 123 # Skipped
     ]
     # Adjust expectation based on exact behavior for dicts without 'role'
     # If dicts without 'role' are kept:
     assert len(filtered) == 3
     assert filtered[0] == {"role": "system", "content": "Valid System"}
     assert filtered[1] == {"role": "user", "content": "User"}
     assert filtered[2] == {"not_a_role": "value"} # Check if this is the intended behavior
     # Verify only one system message remains
     assert len([msg for msg in filtered if isinstance(msg, dict) and msg.get("role") == "system"]) == 1
