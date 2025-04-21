import pytest
from unittest.mock import patch
from swarm.core import output_utils

def test_print_search_progress_box_basic(capsys):
    output_utils.print_search_progress_box(
        op_type="Code Search",
        results=["Found 2 matches."],
        params={"query": "foo", "directory": ".", "filetypes": ".py"},
        result_type="code",
        summary="Searched filesystem for: 'foo'",
        progress_line="Processed 10/100 files...",
        spinner_state="Generating..",
        operation_type="Code Search",
        search_mode="keyword",
        total_lines=100,
        emoji='🔎',
        border='╔'
    )
    captured = capsys.readouterr()
    assert "Code Search" in captured.out
    assert "Results:" in captured.out
    assert "Params:" in captured.out
    assert "Processed 10/100 files" in captured.out
    assert "Generating.." in captured.out
    assert "🔎" in captured.out


def test_print_search_progress_box_semantic(capsys):
    output_utils.print_search_progress_box(
        op_type="Semantic Search",
        results=["No semantic matches found."],
        params={"query": "bar", "directory": ".", "filetypes": ".py", "semantic": True},
        result_type="semantic",
        summary="Analyzed codebase for: 'bar'",
        progress_line="Processed 50/200 files...",
        spinner_state="Generating... Taking longer than expected",
        operation_type="Semantic Search",
        search_mode="semantic",
        total_lines=200,
        emoji='🧠',
        border='╔'
    )
    captured = capsys.readouterr()
    assert "Semantic Search" in captured.out
    assert "semantic matches" in captured.out
    assert "Processed 50/200 files" in captured.out
    assert "Taking longer than expected" in captured.out
    assert "🧠" in captured.out


def test_print_search_progress_box_minimal(capsys):
    output_utils.print_search_progress_box(
        op_type="Quick Search",
        results=["No matches found."],
    )
    captured = capsys.readouterr()
    assert "Quick Search" in captured.out
    assert "No matches found." in captured.out


def test_print_search_progress_box_params_none(capsys):
    output_utils.print_search_progress_box(
        op_type="Test Search",
        results=["Test result"],
        params=None,
        spinner_state=None,
        emoji=None,
        border=None
    )
    captured = capsys.readouterr()
    assert "Test Search" in captured.out
    assert "Test result" in captured.out


def test_print_operation_box_plaintext_fallback(monkeypatch, capsys):
    # Patch is_ansi_capable to always return False
    monkeypatch.setattr("swarm.core.output_utils.is_ansi_capable", lambda: False)
    from swarm.core.output_utils import print_operation_box
    print_operation_box(
        op_type="PlainTest",
        results=["Plain output only."],
        params=None,
        result_type="generic",
        emoji=None,
        border=None
    )
    captured = capsys.readouterr()
    assert "Plain output only." in captured.out
    # Should not contain box drawing chars
    assert "═" not in captured.out and "╔" not in captured.out


def test_print_operation_box_dynamic_width(monkeypatch, capsys):
    # Patch shutil.get_terminal_size to return custom width
    import shutil
    import os
    monkeypatch.setattr(shutil, "get_terminal_size", lambda fallback: os.terminal_size((50, 24)))
    from swarm.core.output_utils import print_operation_box
    print_operation_box(
        op_type="WidthTest",
        results=["Width should be 50 or more."],
        border="╔"
    )
    captured = capsys.readouterr()
    # Should see a box of width at least 40, ideally 50
    assert "╔" in captured.out and len(captured.out.splitlines()[0].replace("\033[94m", "").replace("\033[0m", "")) >= 40


def test_is_ansi_capable_variants(monkeypatch):
    import sys
    import os
    from swarm.core import output_utils
    # Patch sys.stdout.isatty and os.environ["TERM"]
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setitem(os.environ, "TERM", "xterm-256color")
    assert output_utils.is_ansi_capable() is True
    monkeypatch.setitem(os.environ, "TERM", "dumb")
    assert output_utils.is_ansi_capable() is False
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    monkeypatch.setitem(os.environ, "TERM", "xterm-256color")
    assert output_utils.is_ansi_capable() is False


def test_is_non_interactive(monkeypatch):
    import sys
    from swarm.core import output_utils
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    assert output_utils.is_non_interactive() is True
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert output_utils.is_non_interactive() is False
