"""Direct tests for context_utils.get_token_count input handling.

The truncation tests mock this function, so its own preprocessing — None/empty
→ 0, dict key-whitelisting, list/JSON handling, and graceful fallback on weird
input — was never exercised. Assertions avoid depending on tiktoken's exact
counts (the function falls back to a word count when tiktoken is unavailable).
"""
from __future__ import annotations

from swarm.utils.context_utils import get_token_count

MODEL = "gpt-4"


def test_none_and_empty_are_zero():
    assert get_token_count(None, MODEL) == 0
    assert get_token_count("", MODEL) == 0


def test_plain_string_is_positive():
    assert get_token_count("hello world", MODEL) > 0


def test_returns_int_for_all_input_types():
    for value in ["x", {"role": "user", "content": "hi"}, ["a", "b"], 12345, 3.14]:
        assert isinstance(get_token_count(value, MODEL), int)


def test_dict_ignores_non_whitelisted_keys():
    # Only role/content/name/tool_calls/tool_call_id are counted, so an extra
    # internal key must not change the token count.
    base = {"role": "user", "content": "hello there"}
    with_extra = {**base, "internal_secret": "should-not-be-counted", "_meta": 999}
    assert get_token_count(base, MODEL) == get_token_count(with_extra, MODEL)


def test_dict_with_non_string_content_does_not_crash():
    n = get_token_count({"role": "assistant", "content": {"nested": [1, 2, 3]}}, MODEL)
    assert isinstance(n, int) and n > 0


def test_non_serializable_object_falls_back_gracefully():
    class Weird:
        def __repr__(self):
            return "weird-object"

    assert isinstance(get_token_count(Weird(), MODEL), int)
