"""Tests for context_utils._is_valid_message — per-role message validity.

Untested helper that gates which messages survive truncation/validation. The
rules: system/user need string content; assistant needs string content OR a
non-empty tool_calls list; tool needs string content AND a tool_call_id;
anything else (bad type, missing/non-str role, unknown role) is invalid.
"""
from __future__ import annotations

from swarm.utils.context_utils import _is_valid_message


def test_non_dict_is_invalid():
    assert _is_valid_message("not a dict") is False
    assert _is_valid_message(None) is False
    assert _is_valid_message(["role", "user"]) is False


def test_missing_or_non_string_role_is_invalid():
    assert _is_valid_message({"content": "hi"}) is False
    assert _is_valid_message({"role": None, "content": "hi"}) is False
    assert _is_valid_message({"role": 123, "content": "hi"}) is False


def test_system_and_user_need_string_content():
    assert _is_valid_message({"role": "system", "content": "x"}) is True
    assert _is_valid_message({"role": "user", "content": "x"}) is True
    assert _is_valid_message({"role": "user", "content": None}) is False
    assert _is_valid_message({"role": "system", "content": {"not": "str"}}) is False


def test_assistant_valid_with_content_or_tool_calls():
    assert _is_valid_message({"role": "assistant", "content": "answer"}) is True
    assert _is_valid_message(
        {"role": "assistant", "content": None, "tool_calls": [{"id": "c1"}]}
    ) is True
    # neither content nor tool calls → invalid
    assert _is_valid_message({"role": "assistant", "content": None}) is False
    assert _is_valid_message({"role": "assistant", "content": None, "tool_calls": []}) is False


def test_tool_needs_content_and_tool_call_id():
    assert _is_valid_message(
        {"role": "tool", "content": "result", "tool_call_id": "c1"}
    ) is True
    assert _is_valid_message({"role": "tool", "content": "result"}) is False
    assert _is_valid_message({"role": "tool", "content": None, "tool_call_id": "c1"}) is False


def test_unknown_role_is_invalid():
    assert _is_valid_message({"role": "function", "content": "x"}) is False
