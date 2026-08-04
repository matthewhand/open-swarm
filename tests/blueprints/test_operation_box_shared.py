"""Shared rendering tests for ``display_operation_box``.

``display_operation_box`` (swarm.blueprints.common.operation_box_utils) is the
single helper every CLI blueprint uses to render its progress/result boxes.
Its rendering contract used to be re-asserted, near-identically, inside each
blueprint's ``test_*_spinner_and_box.py`` (geese + jeeves had byte-identical
copies). Those duplicates were consolidated here so the shared utility is tested
once. Each blueprint's own spinner *class* and ``run()`` behaviour still live in
their respective test files.
"""
from swarm.blueprints.common.operation_box_utils import display_operation_box


def test_renders_all_fields(capsys):
    display_operation_box(
        title="Test Title",
        content="Test Content",
        result_count=5,
        params={"query": "foo"},
        progress_line=10,
        total_lines=100,
        spinner_state="Generating...",
        emoji="🔍",
    )
    out = capsys.readouterr().out
    assert "Test Content" in out
    assert "Progress: 10/100" in out
    assert "Results: 5" in out
    assert "Query: foo" in out
    assert "Generating..." in out
    assert "🔍" in out


def test_default_emoji(capsys):
    display_operation_box(title="Test Title", content="Test Content")
    out = capsys.readouterr().out
    assert "Test Content" in out
    assert "💡" in out


def test_long_wait_state(capsys):
    display_operation_box(
        title="Test Title",
        content="Test Content",
        spinner_state="Generating... Taking longer than expected",
        emoji="⏳",
    )
    out = capsys.readouterr().out
    assert "Taking longer than expected" in out
    assert "⏳" in out
