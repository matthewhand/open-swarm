"""
Comprehensive tests for message_utils module
===========================================

Tests message filtering, validation, and processing utilities.
"""

import pytest

from src.swarm.utils.message_utils import (
    filter_duplicate_system_messages,
    filter_messages,
    update_null_content,
)


class TestFilterDuplicateSystemMessages:
    """Test filtering of duplicate system messages."""

    def test_filter_duplicate_system_messages_no_duplicates(self):
        """Test filtering when there are no duplicate system messages."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        result = filter_duplicate_system_messages(messages)
        assert result == messages

    def test_filter_duplicate_system_messages_with_duplicates(self):
        """Test filtering when there are duplicate system messages."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "You are also very knowledgeable."},
            {"role": "assistant", "content": "Hi there!"}
        ]

        result = filter_duplicate_system_messages(messages)
        expected = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        assert result == expected

    def test_filter_duplicate_system_messages_multiple_duplicates(self):
        """Test filtering with multiple duplicate system messages."""
        messages = [
            {"role": "system", "content": "System message 1"},
            {"role": "system", "content": "System message 2"},
            {"role": "system", "content": "System message 3"},
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "System message 4"}
        ]

        result = filter_duplicate_system_messages(messages)
        expected = [
            {"role": "system", "content": "System message 1"},
            {"role": "user", "content": "Hello"}
        ]

        assert result == expected

    def test_filter_duplicate_system_messages_empty_list(self):
        """Test filtering with empty message list."""
        result = filter_duplicate_system_messages([])
        assert result == []

    def test_filter_duplicate_system_messages_no_system_messages(self):
        """Test filtering when there are no system messages."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        result = filter_duplicate_system_messages(messages)
        assert result == messages

    def test_filter_duplicate_system_messages_invalid_items(self):
        """Test filtering with invalid/non-dict items."""
        messages = [
            {"role": "system", "content": "Valid system message"},
            "invalid string",
            {"role": "user", "content": "Valid user message"},
            {"invalid": "dict without role"},
            123
        ]

        result = filter_duplicate_system_messages(messages)
        expected = [
            {"role": "system", "content": "Valid system message"},
            {"role": "user", "content": "Valid user message"},
            {"invalid": "dict without role"}
        ]

        assert result == expected


class TestFilterMessages:
    """Test message filtering functionality."""

    def test_filter_messages_valid_messages(self):
        """Test filtering with all valid messages."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        result = filter_messages(messages)
        assert result == messages

    def test_filter_messages_empty_content(self):
        """Test filtering messages with empty content."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "Hi there!"}
        ]

        result = filter_messages(messages)
        expected = [
            {"role": "system", "content": "You are helpful."},
            {"role": "assistant", "content": "Hi there!"}
        ]

        assert result == expected

    def test_filter_messages_whitespace_content(self):
        """Test filtering messages with whitespace-only content."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "   \n\t  "},
            {"role": "assistant", "content": "Hi there!"}
        ]

        result = filter_messages(messages)
        expected = [
            {"role": "system", "content": "You are helpful."},
            {"role": "assistant", "content": "Hi there!"}
        ]

        assert result == expected

    def test_filter_messages_none_content(self):
        """Test filtering messages with None content."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": None},
            {"role": "assistant", "content": "Hi there!"}
        ]

        result = filter_messages(messages)
        expected = [
            {"role": "system", "content": "You are helpful."},
            {"role": "assistant", "content": "Hi there!"}
        ]

        assert result == expected

    def test_filter_messages_with_tool_calls(self):
        """Test filtering messages that have tool calls but no content."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "type": "function"}]},
            {"role": "assistant", "content": "Hi there!"}
        ]

        result = filter_messages(messages)
        expected = [
            {"role": "system", "content": "You are helpful."},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "type": "function"}]},
            {"role": "assistant", "content": "Hi there!"}
        ]

        assert result == expected

    def test_filter_messages_missing_content_key(self):
        """Test filtering messages missing content key."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user"},  # Missing content key
            {"role": "assistant", "content": "Hi there!"}
        ]

        result = filter_messages(messages)
        expected = [
            {"role": "system", "content": "You are helpful."},
            {"role": "assistant", "content": "Hi there!"}
        ]

        assert result == expected

    def test_filter_messages_invalid_input_types(self):
        """Test filtering with invalid input types."""
        # Non-list input
        result = filter_messages("not a list")
        assert result == []

        result = filter_messages(None)
        assert result == []

        result = filter_messages(123)
        assert result == []

    def test_filter_messages_non_dict_items(self):
        """Test filtering with non-dict items in list."""
        messages = [
            {"role": "system", "content": "Valid"},
            "invalid string",
            {"role": "user", "content": "Valid user"},
            123,
            None
        ]

        result = filter_messages(messages)
        expected = [
            {"role": "system", "content": "Valid"},
            {"role": "user", "content": "Valid user"}
        ]

        assert result == expected

    def test_filter_messages_complex_tool_calls(self):
        """Test filtering with complex tool calls."""
        messages = [
            {"role": "assistant", "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "test", "arguments": "{}"}}
            ]},
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "Response"}
        ]

        result = filter_messages(messages)
        assert len(result) == 2  # Should keep tool call message and response
        assert result[0]["role"] == "assistant"
        assert "tool_calls" in result[0]

    def test_filter_messages_empty_list(self):
        """Test filtering with empty list."""
        result = filter_messages([])
        assert result == []


class TestUpdateNullContent:
    """Test null content updating functionality."""

    def test_update_null_content_single_dict_with_null(self):
        """Test updating single dict with null content."""
        message = {"role": "user", "content": None}
        result = update_null_content(message)

        assert result["role"] == "user"
        assert result["content"] == ""
        assert result is message  # Should modify in place

    def test_update_null_content_single_dict_with_content(self):
        """Test updating single dict that already has content."""
        message = {"role": "user", "content": "Hello"}
        result = update_null_content(message)

        assert result["role"] == "user"
        assert result["content"] == "Hello"
        assert result is message

    def test_update_null_content_single_dict_missing_content(self):
        """Test updating single dict missing content key."""
        message = {"role": "user"}
        result = update_null_content(message)

        assert result["role"] == "user"
        assert "content" not in result
        assert result is message

    def test_update_null_content_list_with_nulls(self):
        """Test updating list with null content messages."""
        messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": None},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": None}
        ]

        result = update_null_content(messages)

        assert result[0]["content"] == "System message"
        assert result[1]["content"] == ""
        assert result[2]["content"] == "Response"
        assert result[3]["content"] == ""
        assert result is not messages  # Should return new list

    def test_update_null_content_list_mixed_types(self):
        """Test updating list with mixed message types."""
        messages = [
            {"role": "system", "content": "Valid"},
            {"role": "user", "content": None},
            "invalid string",
            {"role": "assistant", "content": None},
            123
        ]

        result = update_null_content(messages)

        assert result[0]["content"] == "Valid"
        assert result[1]["content"] == ""
        assert result[2] == "invalid string"  # Non-dict should be unchanged
        assert result[3]["content"] == ""
        assert result[4] == 123  # Non-dict should be unchanged

    def test_update_null_content_empty_list(self):
        """Test updating empty list."""
        result = update_null_content([])
        assert result == []

    def test_update_null_content_non_dict_list(self):
        """Test updating list with no dict items."""
        messages = ["string", 123, None]
        result = update_null_content(messages)
        assert result == messages

    def test_update_null_content_invalid_input_types(self):
        """Test updating with invalid input types."""
        # String input
        result = update_null_content("not a dict or list")
        assert result == "not a dict or list"

        # Integer input
        result = update_null_content(42)
        assert result == 42

        # None input
        result = update_null_content(None)
        assert result == None

    def test_update_null_content_nested_structures(self):
        """Test updating nested structures."""
        # This function doesn't handle nested structures, so test that it doesn't crash
        nested = {
            "messages": [
                {"role": "user", "content": None},
                {"role": "assistant", "content": "Response"}
            ]
        }

        result = update_null_content(nested)
        assert result == nested  # Should return unchanged
        assert result["messages"][0]["content"] is None  # Nested null should be unchanged


class TestMessageUtilsIntegration:
    """Integration tests combining multiple message utilities."""

    def test_filter_and_update_null_content(self):
        """Test combining filter_messages and update_null_content."""
        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": None},  # Should be updated to ""
            {"role": "user", "content": ""},    # Should be filtered out
            {"role": "user", "content": "   "}, # Should be filtered out
            {"role": "assistant", "content": "Response"}
        ]

        # First update null content
        updated = update_null_content(messages)

        # Then filter messages
        filtered = filter_messages(updated)

        expected = [
            {"role": "system", "content": "System"},
            {"role": "assistant", "content": "Response"}
        ]

        assert filtered == expected

    def test_duplicate_system_filter_and_null_update(self):
        """Test combining duplicate system filter and null content update."""
        messages = [
            {"role": "system", "content": "First system"},
            {"role": "system", "content": "Second system"},  # Should be filtered
            {"role": "user", "content": None},  # Should be updated
            {"role": "assistant", "content": "Response"}
        ]

        # First update null content
        updated = update_null_content(messages)

        # Then filter duplicates
        filtered = filter_duplicate_system_messages(updated)

        expected = [
            {"role": "system", "content": "First system"},
            {"role": "user", "content": ""},  # Updated from None
            {"role": "assistant", "content": "Response"}
        ]

        assert filtered == expected

    def test_all_filters_combined(self):
        """Test all message utilities working together."""
        messages = [
            {"role": "system", "content": "First system"},
            {"role": "system", "content": "Second system"},  # Duplicate, should be removed
            {"role": "user", "content": None},  # Should be updated to ""
            {"role": "user", "content": ""},    # Should be filtered out
            {"role": "user", "content": "   "}, # Should be filtered out
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Valid message"}
        ]

        # Apply all transformations in sequence
        updated = update_null_content(messages)
        deduplicated = filter_duplicate_system_messages(updated)
        filtered = filter_messages(deduplicated)

        expected = [
            {"role": "system", "content": "First system"},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Valid message"}
        ]

        assert filtered == expected


class TestMessageUtilsEdgeCases:
    """Test edge cases and error conditions."""

    def test_filter_messages_large_input(self):
        """Test filtering with large number of messages."""
        # Create 1000 messages
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(1000)]

        result = filter_messages(messages)
        assert len(result) == 1000
        assert all(msg["content"] == f"Message {i}" for i, msg in enumerate(result))

    def test_update_null_content_deep_copy_behavior(self):
        """Test that update_null_content creates proper copies."""
        original = [{"role": "user", "content": None}]
        result = update_null_content(original)

        # Should be different objects
        assert result is not original
        assert result[0] is not original[0]

        # But content should be updated
        assert result[0]["content"] == ""
        assert original[0]["content"] is None

    def test_filter_duplicate_system_messages_preserves_order(self):
        """Test that duplicate filtering preserves message order."""
        messages = [
            {"role": "system", "content": "System 1"},
            {"role": "user", "content": "User 1"},
            {"role": "system", "content": "System 2"},
            {"role": "assistant", "content": "Assistant 1"},
            {"role": "system", "content": "System 3"},
            {"role": "user", "content": "User 2"}
        ]

        result = filter_duplicate_system_messages(messages)

        expected = [
            {"role": "system", "content": "System 1"},
            {"role": "user", "content": "User 1"},
            {"role": "assistant", "content": "Assistant 1"},
            {"role": "user", "content": "User 2"}
        ]

        assert result == expected

    def test_message_utils_with_unicode_content(self):
        """Test message utilities with Unicode content."""
        messages = [
            {"role": "system", "content": "🚀 System message"},
            {"role": "user", "content": "Hello 🌍"},
            {"role": "assistant", "content": "Hi 👋"}
        ]

        # All utilities should handle Unicode properly
        filtered = filter_messages(messages)
        assert filtered == messages

        deduplicated = filter_duplicate_system_messages(messages)
        assert deduplicated == messages

        updated = update_null_content(messages)
        assert updated == messages