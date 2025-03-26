import pytest
# Import from correct location
from src.swarm.utils.message_utils import update_null_content

def test_update_null_content_list():
    """Test updating None content in a list of message dictionaries."""
    messages = [
        {"role": "system", "content": None}, # Should become ""
        {"role": "user", "content": "Valid"}, # Should stay "Valid"
        {"role": "assistant", "content": None}, # Should become ""
        {"role": "user", "content": ""}, # Should stay ""
        {"role": "assistant"}, # Missing content key, should be untouched
        {"role": "tool", "content": None, "tool_call_id": "123"}, # Should become ""
        None, # Non-dict item
        {"role": "final", "content": None} # Should become ""
    ]
    # Create a copy to check original is not modified (if implemented that way)
    original_messages_copy = [m.copy() if isinstance(m, dict) else m for m in messages]

    updated = update_null_content(messages)

    # Check updated list
    assert updated[0]["content"] == ""
    assert updated[1]["content"] == "Valid"
    assert updated[2]["content"] == ""
    assert updated[3]["content"] == ""
    assert "content" not in updated[4], "Function should not add 'content' key if missing"
    assert updated[5]["content"] == ""
    assert updated[6] is None # Non-dict item should be preserved
    assert updated[7]["content"] == ""

    # Verify original list (or its copies) were not modified if func creates new list
    assert original_messages_copy[0]["content"] is None
    assert original_messages_copy[4] == {"role": "assistant"}
    assert original_messages_copy[5]["content"] is None


def test_update_null_content_single_dict():
    """Test updating None content in a single message dictionary."""
    message_none = {"role": "assistant", "content": None}
    # Test modification in-place behavior if intended, or check returned value
    updated_none = update_null_content(message_none.copy()) # Pass a copy
    assert updated_none["content"] == "", "Content should be empty string"
    # assert message_none["content"] is None # Ensure original dict unchanged if copy was passed

    message_valid = {"role": "user", "content": "Hello"}
    updated_valid = update_null_content(message_valid.copy())
    assert updated_valid["content"] == "Hello"

    message_no_content = {"role": "user"}
    updated_no_content = update_null_content(message_no_content.copy())
    assert "content" not in updated_no_content, "Function should not add 'content' key"

def test_update_null_content_no_change_needed():
    """Test with messages that don't have None content."""
    messages = [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "User"},
        {"role": "assistant", "content": ""}, # Empty string is not None
    ]
    original_messages = [msg.copy() for msg in messages] # Deep copy for comparison
    updated = update_null_content(messages)
    assert updated == original_messages # Should be identical

def test_update_null_content_empty_list_or_invalid_input():
    """Test with empty list or non-list/dict input."""
    assert update_null_content([]) == []
    assert update_null_content(None) is None
    assert update_null_content("a string") == "a string"
    assert update_null_content(123) == 123
