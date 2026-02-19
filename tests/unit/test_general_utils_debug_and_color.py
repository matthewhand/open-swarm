import os
from unittest.mock import patch

import pytest

from src.swarm.utils.general_utils import (
    color_text,
    find_project_root,
    is_debug_enabled,
)


class TestIsDebugEnabled:
    @patch.dict(os.environ, {"SWARM_DEBUG": "1", "DEBUG": "0", "OPEN_SWARM_DEBUG": "off"}, clear=False)
    def test_truthy_value_enables_debug(self):
        assert is_debug_enabled() is True

    @patch.dict(os.environ, {"SWARM_DEBUG": "false", "DEBUG": "0", "OPEN_SWARM_DEBUG": "off"}, clear=False)
    def test_falsey_values_disable_debug(self):
        assert is_debug_enabled() is False

    @patch.dict(os.environ, {"SWARM_DEBUG": "", "DEBUG": "True"}, clear=False)
    def test_any_var_truthy_triggers_debug(self):
        assert is_debug_enabled() is True

    @patch.dict(os.environ, {"SWARM_DEBUG": "False", "DEBUG": "OFF", "OPEN_SWARM_DEBUG": "nope"}, clear=False)
    def test_non_standard_truthy_strings(self):
        # "nope" is not in the falsey set, so considered truthy
        assert is_debug_enabled() is True


class TestColorText:
    def test_color_wraps_text_with_ansi(self):
        txt = "hello"
        out = color_text(txt, "red")
        # Starts with ESC [, ends with reset, and contains original text
        assert out.startswith("\033[")
        assert out.endswith("\033[0m")
        assert txt in out

    def test_unknown_color_returns_uncolored_text_with_reset(self):
        txt = "plain"
        out = color_text(txt, "unknown-color")
        # If color unknown, prefix is empty but reset is still appended per implementation
        assert out.endswith("\033[0m")
        assert txt in out


class TestFindProjectRoot:
    def test_finds_marker_in_parent(self, tmp_path):
        # Create nested structure with a .git marker at the top
        project_root = tmp_path / "repo"
        nested = project_root / "a" / "b" / "c"
        nested.mkdir(parents=True)
        (project_root / ".git").mkdir()

        found = find_project_root(str(nested))
        assert os.path.abspath(found) == os.path.abspath(str(project_root))

    def test_raises_when_marker_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            find_project_root(str(tmp_path))

