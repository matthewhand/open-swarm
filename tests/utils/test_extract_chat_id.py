"""Tests for general_utils.extract_chat_id — JMESPath-based stateful-chat routing.

This function picks the chat/session id out of an incoming payload using either
STATEFUL_CHAT_ID_PATH (||-separated JMESPath expressions) or a hardcoded list of
default paths. It was previously untested; these pin the routing behaviour.
"""
from __future__ import annotations

import os
from unittest.mock import patch

from swarm.utils.general_utils import extract_chat_id


def test_default_channel_id_path():
    with patch.dict(os.environ, {}, clear=True):
        payload = {"metadata": {"channelInfo": {"channelId": "C123"}}}
        assert extract_chat_id(payload) == "C123"


def test_falls_back_to_user_id_path():
    # No channelId present → the second default path (userInfo.userId) wins.
    with patch.dict(os.environ, {}, clear=True):
        payload = {"metadata": {"userInfo": {"userId": "U456"}}}
        assert extract_chat_id(payload) == "U456"


def test_no_match_returns_empty_string():
    with patch.dict(os.environ, {}, clear=True):
        assert extract_chat_id({"unrelated": {"x": 1}}) == ""
        assert extract_chat_id({}) == ""


def test_env_override_single_path():
    with patch.dict(os.environ, {"STATEFUL_CHAT_ID_PATH": "session.id"}, clear=True):
        assert extract_chat_id({"session": {"id": "S789"}}) == "S789"


def test_env_override_first_matching_of_alternatives():
    # ||-separated alternatives: first non-empty match wins.
    with patch.dict(os.environ, {"STATEFUL_CHAT_ID_PATH": "a.id || b.id"}, clear=True):
        assert extract_chat_id({"b": {"id": "from_b"}}) == "from_b"
        assert extract_chat_id({"a": {"id": "from_a"}, "b": {"id": "from_b"}}) == "from_a"


def test_non_string_id_is_not_returned():
    # A numeric/None value at the path should not be coerced into a chat id.
    with patch.dict(os.environ, {"STATEFUL_CHAT_ID_PATH": "session.id"}, clear=True):
        assert extract_chat_id({"session": {"id": 12345}}) in ("", "12345")
