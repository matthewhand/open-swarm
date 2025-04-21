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
