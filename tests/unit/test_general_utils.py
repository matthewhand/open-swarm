"""Unit tests for swarm.utils.general_utils.

Ported from archive/local-main-2025-04 and adapted to current main:
- color_text() on main appends the ANSI reset code even for unknown colors,
  so the invalid-color test asserts that behaviour instead of bare text.
"""
import json
import os
import tempfile
from datetime import datetime
from unittest.mock import patch

import pytest

from swarm.utils.general_utils import (
    color_text,
    custom_json_dumps,
    extract_chat_id,
    find_project_root,
    is_debug_enabled,
    serialize_datetime,
)


class TestFindProjectRoot:
    def test_find_project_root_with_git(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a subdirectory
            sub_dir = os.path.join(temp_dir, "sub", "deep")
            os.makedirs(sub_dir)

            # Create .git in temp_dir
            git_dir = os.path.join(temp_dir, ".git")
            os.makedirs(git_dir)

            # Should find from subdir
            result = find_project_root(sub_dir)
            assert result == temp_dir

    def test_find_project_root_with_custom_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sub_dir = os.path.join(temp_dir, "sub")
            os.makedirs(sub_dir)

            # Create custom marker
            marker_file = os.path.join(temp_dir, "marker.txt")
            with open(marker_file, "w") as f:
                f.write("test")

            result = find_project_root(sub_dir, marker="marker.txt")
            assert result == temp_dir

    def test_find_project_root_not_found(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(FileNotFoundError, match="Project root with marker '.git' not found"):
                find_project_root(temp_dir)


class TestColorText:
    def test_color_text_valid_colors(self):
        text = "Hello"
        for color in ["red", "green", "yellow", "blue", "magenta", "cyan", "white"]:
            result = color_text(text, color)
            assert text in result
            assert result.startswith("\033[9")
            assert result.endswith("\033[0m")

    def test_color_text_invalid_color(self):
        text = "Hello"
        result = color_text(text, "invalid")
        # No color start code is added for unknown colors; the reset code is
        # always appended by the current implementation.
        assert result == text + "\033[0m"

    def test_color_text_default_white(self):
        text = "Hello"
        result = color_text(text)
        assert text in result
        assert "\033[97m" in result


class TestIsDebugEnabled:
    @patch.dict(os.environ, {}, clear=True)
    def test_no_debug_vars(self):
        assert not is_debug_enabled()

    @patch.dict(os.environ, {"SWARM_DEBUG": "1"})
    def test_swarm_debug_true(self):
        assert is_debug_enabled()

    @patch.dict(os.environ, {"DEBUG": "true"})
    def test_debug_true(self):
        assert is_debug_enabled()

    @patch.dict(os.environ, {"OPEN_SWARM_DEBUG": "yes"})
    def test_open_swarm_debug_true(self):
        assert is_debug_enabled()

    @patch.dict(os.environ, {"SWARM_DEBUG": "0"}, clear=True)
    def test_swarm_debug_false(self):
        assert not is_debug_enabled()

    @patch.dict(os.environ, {"DEBUG": "false"}, clear=True)
    def test_debug_false(self):
        assert not is_debug_enabled()

    @patch.dict(os.environ, {"SWARM_DEBUG": "off"}, clear=True)
    def test_swarm_debug_off(self):
        assert not is_debug_enabled()


class TestExtractChatId:
    @patch.dict(os.environ, {}, clear=True)
    def test_extract_chat_id_from_metadata_channel(self):
        payload = {
            "metadata": {
                "channelInfo": {"channelId": "channel123"}
            }
        }
        result = extract_chat_id(payload)
        assert result == "channel123"

    @patch.dict(os.environ, {}, clear=True)
    def test_extract_chat_id_from_metadata_user(self):
        payload = {
            "metadata": {
                "userInfo": {"userId": "user456"}
            }
        }
        result = extract_chat_id(payload)
        assert result == "user456"

    @patch.dict(os.environ, {}, clear=True)
    def test_extract_chat_id_from_tool_calls(self):
        payload = {
            "messages": [
                {
                    "tool_calls": [
                        {
                            "function": {
                                "arguments": '{"chat_id": "tool789"}'
                            }
                        }
                    ]
                }
            ]
        }
        result = extract_chat_id(payload)
        assert result == "tool789"

    @patch.dict(os.environ, {"STATEFUL_CHAT_ID_PATH": "custom.path"})
    def test_extract_chat_id_from_env_var(self):
        payload = {"custom": {"path": "env999"}}
        result = extract_chat_id(payload)
        assert result == "env999"

    @patch.dict(os.environ, {}, clear=True)
    def test_extract_chat_id_no_match(self):
        payload = {"some": "data"}
        result = extract_chat_id(payload)
        assert result == ""

    @patch.dict(os.environ, {"STATEFUL_CHAT_ID_PATH": "nonexistent.path"})
    def test_extract_chat_id_env_no_match(self):
        payload = {"some": "data"}
        result = extract_chat_id(payload)
        assert result == ""


class TestSerializeDatetime:
    def test_serialize_datetime(self):
        dt = datetime(2023, 10, 1, 12, 30, 45)
        result = serialize_datetime(dt)
        assert result == "2023-10-01T12:30:45"

    def test_serialize_string(self):
        s = "already_string"
        result = serialize_datetime(s)
        assert result == s

    def test_serialize_invalid_type(self):
        with pytest.raises(TypeError, match="Type .* not serializable"):
            serialize_datetime(123)


class TestCustomJsonDumps:
    def test_custom_json_dumps_with_datetime(self):
        data = {"timestamp": datetime(2023, 10, 1, 12, 30, 45)}
        result = custom_json_dumps(data)
        parsed = json.loads(result)
        assert parsed["timestamp"] == "2023-10-01T12:30:45"

    def test_custom_json_dumps_without_datetime(self):
        data = {"key": "value", "number": 42}
        result = custom_json_dumps(data)
        parsed = json.loads(result)
        assert parsed == data
