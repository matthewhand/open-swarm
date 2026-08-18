"""Failure-path coverage for logged Exception handlers in pair truncation.

When msg_tokens holds a negative count, the pair-search asserts fail and the
handlers must log a warning and fall back to a high token cost instead of a
silent bare except.
"""
from __future__ import annotations

import os
from unittest.mock import patch

from swarm.utils.context_utils import truncate_message_history

MODEL = "gpt-4"


def test_pairs_logs_bad_tokens_on_assistant_lookup(monkeypatch):
    """Case 1 pair search: negative assistant tokens trip the logged handler."""
    os.environ["SWARM_TRUNCATION_MODE"] = "pairs"
    try:

        def token_count(text, model):
            if not isinstance(text, dict):
                return 10
            role = text.get("role")
            if role == "system":
                return 5
            if role == "assistant":
                return -1  # stored in msg_tokens; assert fails in Case 1 lookup
            return 40

        monkeypatch.setattr("swarm.utils.context_utils.get_token_count", token_count)

        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "please call the tool"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "c1", "function": {"name": "ToolA", "arguments": "{}"}}
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": "tool result"},
        ]

        # Force truncation so the sophisticated loop (and Case 1) runs.
        with patch("swarm.utils.context_utils.logger.warning") as warn:
            result = truncate_message_history(messages, MODEL, max_tokens=80, max_messages=10)

        assert isinstance(result, list)
        assert any(
            "Bad tokens" in str(call.args[0]) for call in warn.call_args_list if call.args
        ), f"expected Bad tokens warning, got: {warn.call_args_list}"
    finally:
        os.environ.pop("SWARM_TRUNCATION_MODE", None)


def test_pairs_logs_bad_tokens_on_tool_lookup(monkeypatch):
    """Case 2 pair search: negative tool tokens trip the logged handler."""
    os.environ["SWARM_TRUNCATION_MODE"] = "pairs"
    try:

        def token_count(text, model):
            if not isinstance(text, dict):
                return 10
            role = text.get("role")
            if role == "system":
                return 5
            if role == "tool":
                return -1  # stored in msg_tokens; assert fails in Case 2 lookup
            return 40

        monkeypatch.setattr("swarm.utils.context_utils.get_token_count", token_count)

        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "please call the tool"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "c1", "function": {"name": "ToolA", "arguments": "{}"}}
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": "tool result"},
            {"role": "assistant", "content": "done"},
        ]

        with patch("swarm.utils.context_utils.logger.warning") as warn:
            result = truncate_message_history(messages, MODEL, max_tokens=100, max_messages=10)

        assert isinstance(result, list)
        assert any(
            "Bad tokens" in str(call.args[0]) for call in warn.call_args_list if call.args
        ), f"expected Bad tokens warning, got: {warn.call_args_list}"
    finally:
        os.environ.pop("SWARM_TRUNCATION_MODE", None)
