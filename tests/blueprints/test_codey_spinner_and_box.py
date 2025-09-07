import io
import sys

import pytest
from swarm.blueprints.codey.blueprint_codey import CodeySpinner
from swarm.blueprints.common.operation_box_utils import display_operation_box


@pytest.mark.parametrize("frame_idx,expected", [
    (0, "Generating."),
    (1, "Generating.."),
    (2, "Generating..."),
    (3, "Running..."),
])
def test_codey_spinner_frames(frame_idx, expected):
    spinner = CodeySpinner()
    spinner.start()
    for _ in range(frame_idx):
        spinner._spin()
    assert spinner.current_spinner_state() == expected

def test_codey_spinner_long_wait():
    spinner = CodeySpinner()
    spinner.start()
    spinner._start_time -= 15
    spinner._spin()
    assert spinner.current_spinner_state() == "Generating... Taking longer than expected"

def test_display_operation_box_basic(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    display_operation_box(
        title="Test Title",
        content="Test Content",
        result_count=5,
        params={'query': 'foo'},
        progress_line=10,
        total_lines=100,
        spinner_state="Generating...",
        emoji="💻"
    )
    out = buf.getvalue()
    assert "Test Content" in out
    assert "Progress: 10/100" in out
    assert "Results: 5" in out
    assert "Query: foo" in out
    assert "Generating..." in out
    assert "💻" in out

def test_display_operation_box_long_wait(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    display_operation_box(
        title="Test Title",
        content="Test Content",
        spinner_state="Generating... Taking longer than expected",
        emoji="⏳"
    )
    out = buf.getvalue()
    assert "Taking longer than expected" in out
    assert "⏳" in out
