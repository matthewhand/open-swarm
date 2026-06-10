import pytest
from swarm.util import merge_fields, merge_chunk

class TestMergeFields:
    """Tests for the merge_fields utility."""

    def test_merge_fields_append_strings(self):
        """Test that string values are appended to existing strings."""
        target = {"content": "Hello"}
        source = {"content": " world"}
        merge_fields(target, source)
        assert target["content"] == "Hello world"

    def test_merge_fields_nested_dict(self):
        """Test recursive merging of nested dictionaries."""
        target = {"meta": {"author": "Alice"}}
        source = {"meta": {"title": "Story"}}
        merge_fields(target, source)
        assert target["meta"] == {"author": "Alice", "title": "Story"}

    def test_merge_fields_new_key(self):
        """Test merging a key that doesn't exist in target."""
        target = {}
        source = {"new_key": "value"}
        merge_fields(target, source)
        assert target["new_key"] == "value"

    def test_merge_fields_ignore_non_string_non_dict(self):
        """Test that non-string and non-dict values are ignored."""
        target = {"count": 1}
        source = {"count": 2}
        merge_fields(target, source)
        assert target["count"] == 1

    def test_merge_fields_none_value(self):
        """Test that None values in source are ignored."""
        target = {"key": "value"}
        source = {"key": None}
        merge_fields(target, source)
        assert target["key"] == "value"


class TestMergeChunk:
    """Tests for the merge_chunk utility."""

    def test_merge_chunk_content(self):
        """Test merging content chunks."""
        final_response = {"content": "Starting"}
        delta = {"content": " more content"}
        merge_chunk(final_response, delta)
        assert final_response["content"] == "Starting more content"

    def test_merge_chunk_pop_role(self):
        """Test that 'role' is removed from delta and not merged into final_response."""
        final_response = {}
        delta = {"role": "assistant", "content": "Hi"}
        merge_chunk(final_response, delta)
        assert "role" not in final_response
        assert final_response["content"] == "Hi"

    def test_merge_chunk_tool_calls_incremental(self):
        """Test merging tool calls incrementally."""
        final_response = {}

        # First chunk for tool call at index 0
        delta1 = {
            "tool_calls": [
                {"index": 0, "id": "call_1", "function": {"name": "get_weather"}}
            ]
        }
        merge_chunk(final_response, delta1)

        assert final_response["tool_calls"][0]["id"] == "call_1"
        assert final_response["tool_calls"][0]["function"]["name"] == "get_weather"

        # Second chunk for tool call at index 0 (incremental arguments)
        delta2 = {
            "tool_calls": [
                {"index": 0, "function": {"arguments": '{"loca'}}
            ]
        }
        merge_chunk(final_response, delta2)

        assert final_response["tool_calls"][0]["function"]["arguments"] == '{"loca'

        # Third chunk for tool call at index 0 (more arguments)
        delta3 = {
            "tool_calls": [
                {"index": 0, "function": {"arguments": 'tion": "Paris"}'}}
            ]
        }
        merge_chunk(final_response, delta3)

        assert final_response["tool_calls"][0]["function"]["arguments"] == '{"location": "Paris"}'

    def test_merge_chunk_multiple_tool_calls_sequential(self):
        """Test merging multiple tool calls that arrive in separate chunks."""
        final_response = {}

        # Tool call 0
        delta0 = {"tool_calls": [{"index": 0, "id": "id0", "function": {"name": "func0"}}]}
        merge_chunk(final_response, delta0)

        # Tool call 1
        delta1 = {"tool_calls": [{"index": 1, "id": "id1", "function": {"name": "func1"}}]}
        merge_chunk(final_response, delta1)

        assert final_response["tool_calls"][0]["id"] == "id0"
        assert final_response["tool_calls"][1]["id"] == "id1"

    def test_merge_chunk_tool_calls_default_index(self):
        """Test merging tool call when index is missing (should default to 0)."""
        final_response = {}
        delta = {"tool_calls": [{"id": "call_default", "function": {"name": "default_func"}}]}
        merge_chunk(final_response, delta)

        # In merge_chunk, final_response["tool_calls"] is a dictionary mapping index (int) to tool call details
        assert isinstance(final_response["tool_calls"], dict)
        assert 0 in final_response["tool_calls"]
        assert final_response["tool_calls"][0]["id"] == "call_default"
