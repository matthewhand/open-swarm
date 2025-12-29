import io
import time

import pytest

from swarm.core.output_utils import JeevesSpinner
from swarm.core.output_utils import print_operation_box as display_operation_box_core

# Define JEEVES_SPINNER_STATES locally for the progressive tool test if it's not easily importable
# This is used by test_display_operation_box_progress in the other file.
# For this file, we use JeevesSpinner.SPINNER_STATES directly.

@pytest.mark.parametrize("frame_idx,expected_state", [
    (0, JeevesSpinner.SPINNER_STATES[0]),
    (1, JeevesSpinner.SPINNER_STATES[1]),
    (2, JeevesSpinner.SPINNER_STATES[2]),
    (3, JeevesSpinner.SPINNER_STATES[3]),
    (4, JeevesSpinner.SPINNER_STATES[4]),
    (5, JeevesSpinner.SPINNER_STATES[0]),
])
def test_jeeves_spinner_frames(frame_idx, expected_state):
    spinner = JeevesSpinner()
    spinner._start_time = time.time()
    spinner._current_frame = frame_idx
    assert spinner.current_spinner_state() == expected_state

def test_jeeves_spinner_long_wait():
    spinner = JeevesSpinner()
    spinner.is_test_mode = False
    spinner._start_time = time.time() - (JeevesSpinner.SLOW_THRESHOLD + 1)
    spinner._running = True
    assert spinner.current_spinner_state() == JeevesSpinner.LONG_WAIT_MSG
    spinner._running = False

def test_display_operation_box_basic(monkeypatch):
    buf = io.StringIO()
    from rich.console import Console
    # Create a console that records to the buffer, disable color for simpler assertion
    console_capture = Console(file=buf, width=120, color_system=None, legacy_windows=True)

    display_operation_box_core(
        title="Test Title",
        content="Test Content",
        result_count=5,
        params={'query': 'foo'},
        progress_line="10/100", # String as per typical usage
        total_lines=100,
        spinner_state="Generating...",
        emoji="🔍",
        style="info", # This will map to "blue" border
        console=console_capture
    )
    out = buf.getvalue()
    # No need to strip ANSI if color_system=None

    assert "Test Title" in out
    assert "Test Content" in out
    assert "Progress: 10/100" in out
    assert "Results: 5" in out
    assert "Parameters: query=foo" in out
    assert "[Generating...]" in out
    assert "🔍" in out

def test_display_operation_box_long_wait(monkeypatch):
    buf = io.StringIO()
    from rich.console import Console
    console_capture = Console(file=buf, width=120, color_system=None, legacy_windows=True)

    display_operation_box_core(
        title="Test Title",
        content="Test Content",
        spinner_state=JeevesSpinner.LONG_WAIT_MSG,
        emoji="⏳",
        style="warning", # This will map to "yellow" border
        console=console_capture
    )
    out = buf.getvalue()

    assert "Test Title" in out
    assert JeevesSpinner.LONG_WAIT_MSG in out
    assert "⏳" in out
