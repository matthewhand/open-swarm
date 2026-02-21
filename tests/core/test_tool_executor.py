"""
Unit tests for src/swarm/tool_executor.py

Covers:
- redact_sensitive_data: redaction behavior for dicts, lists, strings
- handle_function_result: result processing and agent handoffs
- handle_tool_calls: tool execution happy path and edge cases
"""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

from swarm.tool_executor import (
    handle_function_result,
    handle_tool_calls,
    redact_sensitive_data,
)
from swarm.types import Agent, Result


# =============================================================================
# redact_sensitive_data tests
# =============================================================================


class TestRedactSensitiveData:
    """Tests for redact_sensitive_data function."""

    def test_redacts_dict_with_sensitive_keys(self):
        """Keys containing 'key', 'token', 'secret', 'password', 'auth' are redacted."""
        data = {
            "api_key": "sk-1234567890abcdef",  # 19 chars
            "token": "tok-abcdef123456",  # 16 chars
            "client_secret": "secretvalue",  # 11 chars
            "password": "hunter2",  # 7 chars
            "auth_header": "Bearer xyz",  # 10 chars
        }
        redacted = redact_sensitive_data(data)

        # Long strings (>4 chars) get partial redaction: first 2 + * (len-4) + last 2
        # sk-1234567890abcdef (19 chars) -> sk + 15 asterisks + ef
        assert redacted["api_key"] == "sk" + "*" * 15 + "ef"
        # tok-abcdef123456 (16 chars) -> to + 12 asterisks + 56
        assert redacted["token"] == "to" + "*" * 12 + "56"
        # secretvalue (11 chars) -> se + 7 asterisks + ue
        assert redacted["client_secret"] == "se" + "*" * 7 + "ue"
        # hunter2 (7 chars) -> hu + 3 asterisks + r2
        assert redacted["password"] == "hu" + "*" * 3 + "r2"
        # Bearer xyz (10 chars) -> Be + 6 asterisks + yz
        assert redacted["auth_header"] == "Be" + "*" * 6 + "yz"

    def test_redacts_nested_dicts(self):
        """Nested dictionaries are recursively redacted."""
        data = {
            "nested": {
                "api_key": "sk-test-key",  # 11 chars
                "normal_field": "visible",
            }
        }
        redacted = redact_sensitive_data(data)

        # sk-test-key (11 chars) -> sk + 7 asterisks + ey
        assert redacted["nested"]["api_key"] == "sk" + "*" * 7 + "ey"
        assert redacted["nested"]["normal_field"] == "visible"

    def test_redacts_lists(self):
        """Lists are recursively processed."""
        data = [
            {"api_key": "sk-secret"},  # 9 chars
            "plain string",
            {"nested": {"token": "abc123xyz"}},  # 9 chars
        ]
        redacted = redact_sensitive_data(data)

        # sk-secret (9 chars) -> sk + 5 asterisks + et
        assert redacted[0]["api_key"] == "sk" + "*" * 5 + "et"
        assert redacted[1] == "plain string"
        # abc123xyz (9 chars) -> ab + 5 asterisks + yz
        assert redacted[2]["nested"]["token"] == "ab" + "*" * 5 + "yz"

    def test_redacts_strings_with_api_key_patterns(self):
        """Strings containing API key patterns are redacted."""
        # Pattern: sk- prefix
        assert redact_sensitive_data("sk-1234567890") == "***REDACTED***"
        # Pattern: Bearer prefix
        assert redact_sensitive_data("Bearer token123") == "***REDACTED***"
        # Pattern: Basic auth prefix
        assert redact_sensitive_data("Basic dXNlcjpwYXNz") == "***REDACTED***"
        # Pattern: JWT-like (eyJ prefix)
        assert redact_sensitive_data("eyJhbGciOiJIUzI1NiJ9") == "***REDACTED***"

    def test_does_not_redact_normal_strings(self):
        """Normal strings without sensitive patterns pass through."""
        assert redact_sensitive_data("hello world") == "hello world"
        assert redact_sensitive_data("not-sensitive-key") == "not-sensitive-key"

    def test_handles_non_string_values_in_dict(self):
        """Non-string values in sensitive fields get '***'."""
        data = {
            "api_key": 12345,
            "token": None,
            "secret": True,
        }
        redacted = redact_sensitive_data(data)

        assert redacted["api_key"] == "***"
        assert redacted["token"] == "***"
        assert redacted["secret"] == "***"

    def test_handles_empty_and_none_inputs(self):
        """Empty containers and None pass through."""
        assert redact_sensitive_data({}) == {}
        assert redact_sensitive_data([]) == []
        assert redact_sensitive_data(None) is None
        assert redact_sensitive_data("") == ""

    def test_short_sensitive_values_get_masked(self):
        """Short sensitive values (<=4 chars) get '***'."""
        data = {
            "api_key": "abcd",  # 4 chars - gets ***
            "token": "xyz",  # 3 chars - gets ***
        }
        redacted = redact_sensitive_data(data)

        assert redacted["api_key"] == "***"
        assert redacted["token"] == "***"


# =============================================================================
# handle_function_result tests
# =============================================================================


class TestHandleFunctionResult:
    """Tests for handle_function_result function."""

    def test_returns_result_unchanged(self):
        """If result is already a Result, return as-is."""
        result = Result(value="test output", context_variables={"foo": "bar"})
        processed = handle_function_result(result, debug=False)

        assert processed is result

    def test_converts_agent_to_handoff_result(self):
        """If result is an Agent, creates a handoff Result."""
        agent = Agent(name="TestAgent", instructions="Test instructions")
        processed = handle_function_result(agent, debug=False)

        assert isinstance(processed, Result)
        assert processed.agent is agent
        assert "Handoff to agent TestAgent" in processed.value

    def test_converts_dict_to_json_string(self):
        """Dicts are JSON-serialized."""
        result = {"status": "success", "count": 42}
        processed = handle_function_result(result, debug=False)

        assert isinstance(processed, Result)
        assert json.loads(processed.value) == result

    def test_converts_list_to_json_string(self):
        """Lists are JSON-serialized."""
        result = [1, 2, 3, "four"]
        processed = handle_function_result(result, debug=False)

        assert isinstance(processed, Result)
        assert json.loads(processed.value) == result

    def test_converts_string_directly(self):
        """Strings are used directly as value."""
        processed = handle_function_result("plain string result", debug=False)

        assert isinstance(processed, Result)
        assert processed.value == "plain string result"

    def test_converts_other_types_to_string(self):
        """Other types are stringified."""
        processed = handle_function_result(42, debug=False)

        assert isinstance(processed, Result)
        assert processed.value == "42"

    def test_debug_logging(self):
        """Debug mode logs result processing info."""
        with patch("swarm.tool_executor.logger") as mock_logger:
            handle_function_result("test", debug=True)
            mock_logger.debug.assert_called()


# =============================================================================
# handle_tool_calls tests
# =============================================================================


def make_tool_call(tool_id: str, name: str, arguments: str) -> ChatCompletionMessageToolCall:
    """Helper to create a ChatCompletionMessageToolCall for testing."""
    return ChatCompletionMessageToolCall(
        id=tool_id,
        function=Function(name=name, arguments=arguments),
        type="function",
    )


class TestHandleToolCalls:
    """Tests for handle_tool_calls async function."""

    @pytest.mark.asyncio
    async def test_empty_tool_calls_returns_empty_response(self):
        """Empty or None tool_calls returns empty Response."""
        response = await handle_tool_calls([], [], {}, debug=False)
        assert response.messages == []
        assert response.agent is None

        response = await handle_tool_calls(None, [], {}, debug=False)
        assert response.messages == []

    @pytest.mark.asyncio
    async def test_executes_tool_and_returns_result(self):
        """Tool is executed and result is added to messages."""
        tool_call = make_tool_call("call-123", "test_tool", '{"arg1": "value1"}')

        def test_tool(arg1):
            return f"result: {arg1}"

        response = await handle_tool_calls(
            [tool_call], [test_tool], {}, debug=False
        )

        assert len(response.messages) == 1
        assert response.messages[0]["role"] == "tool"
        assert response.messages[0]["tool_call_id"] == "call-123"
        assert response.messages[0]["name"] == "test_tool"
        assert response.messages[0]["content"] == "result: value1"

    @pytest.mark.asyncio
    async def test_handles_async_tool(self):
        """Async tools are awaited."""
        tool_call = make_tool_call("call-async", "async_tool", "{}")

        async def async_tool():
            await asyncio.sleep(0.01)
            return "async result"

        response = await handle_tool_calls(
            [tool_call], [async_tool], {}, debug=False
        )

        assert response.messages[0]["content"] == "async result"

    @pytest.mark.asyncio
    async def test_injects_context_variables(self):
        """Context variables are injected if function expects them."""
        tool_call = make_tool_call("call-ctx", "ctx_tool", "{}")

        def ctx_tool(context_variables):
            return f"ctx: {context_variables.get('key', 'none')}"

        response = await handle_tool_calls(
            [tool_call], [ctx_tool], {"key": "value"}, debug=False
        )

        assert response.messages[0]["content"] == "ctx: value"

    @pytest.mark.asyncio
    async def test_updates_context_from_result(self):
        """Context variables from Result are captured in response."""
        tool_call = make_tool_call("call-update", "update_tool", "{}")

        def update_tool():
            return Result(
                value="done",
                context_variables={"new_key": "new_value"}
            )

        response = await handle_tool_calls(
            [tool_call], [update_tool], {"existing": "kept"}, debug=False
        )

        # The response captures context variable updates from tool results
        assert response.context_variables["new_key"] == "new_value"

    @pytest.mark.asyncio
    async def test_handles_agent_handoff(self):
        """Agent handoff from Result is captured."""
        tool_call = make_tool_call("call-handoff", "handoff_tool", "{}")

        target_agent = Agent(name="TargetAgent", instructions="Target")

        def handoff_tool():
            return Result(value="handoff", agent=target_agent)

        response = await handle_tool_calls(
            [tool_call], [handoff_tool], {}, debug=False
        )

        assert response.agent is target_agent

    @pytest.mark.asyncio
    async def test_handles_missing_tool_gracefully(self):
        """Missing tool returns error message."""
        tool_call = make_tool_call("call-missing", "nonexistent_tool", "{}")

        response = await handle_tool_calls(
            [tool_call], [], {}, debug=False
        )

        assert len(response.messages) == 1
        error_data = json.loads(response.messages[0]["content"])
        assert "error" in error_data
        assert "not available" in error_data["error"]

    @pytest.mark.asyncio
    async def test_handles_invalid_json_arguments(self):
        """Invalid JSON arguments are handled gracefully."""
        tool_call = make_tool_call("call-bad-json", "test_tool", "not valid json")

        def test_tool(**kwargs):
            return "ok"

        response = await handle_tool_calls(
            [tool_call], [test_tool], {}, debug=False
        )

        # Should still execute with empty args
        assert response.messages[0]["content"] == "ok"

    @pytest.mark.asyncio
    async def test_handles_tool_exception(self):
        """Tool exceptions are caught and returned as error messages."""
        tool_call = make_tool_call("call-error", "failing_tool", "{}")

        def failing_tool():
            raise ValueError("Tool failed!")

        response = await handle_tool_calls(
            [tool_call], [failing_tool], {}, debug=False
        )

        error_data = json.loads(response.messages[0]["content"])
        assert "error" in error_data
        assert "Tool failed!" in error_data["error"]

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self):
        """Multiple tool calls are processed in order."""
        tool_call_1 = make_tool_call("call-1", "tool_a", '{"x": 1}')
        tool_call_2 = make_tool_call("call-2", "tool_b", '{"y": 2}')

        def tool_a(x):
            return f"a: {x}"

        def tool_b(y):
            return f"b: {y}"

        response = await handle_tool_calls(
            [tool_call_1, tool_call_2], [tool_a, tool_b], {}, debug=False
        )

        assert len(response.messages) == 2
        assert response.messages[0]["content"] == "a: 1"
        assert response.messages[1]["content"] == "b: 2"

    @pytest.mark.asyncio
    async def test_invalid_tool_call_item_skipped(self):
        """Non-ChatCompletionMessageToolCall items are skipped."""
        invalid_item = {"not": "a tool call"}

        response = await handle_tool_calls(
            [invalid_item], [], {}, debug=False
        )

        assert response.messages == []

    @pytest.mark.asyncio
    async def test_tool_call_missing_name_or_id(self):
        """Tool calls missing name or ID generate error message."""
        # Create a tool call with None name by using a mock
        tool_call = make_tool_call("call-test", "test_tool", "{}")
        # Manually set to None to test the error path
        tool_call.function.name = None

        response = await handle_tool_calls(
            [tool_call], [], {}, debug=False
        )

        # Should have error message
        assert len(response.messages) == 1
        error_data = json.loads(response.messages[0]["content"])
        assert "error" in error_data

    @pytest.mark.asyncio
    async def test_tool_with_dict_return_value(self):
        """Tools returning dicts have them JSON-serialized."""
        tool_call = make_tool_call("call-dict", "dict_tool", "{}")

        def dict_tool():
            return {"status": "success", "items": [1, 2, 3]}

        response = await handle_tool_calls(
            [tool_call], [dict_tool], {}, debug=False
        )

        content = response.messages[0]["content"]
        parsed = json.loads(content)
        assert parsed["status"] == "success"
        assert parsed["items"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_tool_returns_agent_for_handoff(self):
        """Tools returning an Agent directly trigger handoff."""
        tool_call = make_tool_call("call-agent", "agent_tool", "{}")

        target_agent = Agent(name="SpecialistAgent", instructions="You are a specialist")

        def agent_tool():
            return target_agent

        response = await handle_tool_calls(
            [tool_call], [agent_tool], {}, debug=False
        )

        assert response.agent is target_agent
