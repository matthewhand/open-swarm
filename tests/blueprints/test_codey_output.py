import io
import sys

from swarm.blueprints.codey.blueprint_codey import CodeyBlueprint


def test_codey_search_result_box_output(monkeypatch):
    # Capture stdout
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    blueprint = CodeyBlueprint(blueprint_id="test-search-output")
    blueprint.test_print_search_results()
    output = buf.getvalue()
    # Check for boxed output and summary lines
    assert "Code Search" in output
    assert "Semantic Search" in output
    assert "[Code Search Results]" in output
    assert "[Semantic Search Results]" in output
    assert "Results:" in output
    assert "Params" in output or "query" in output
    # Check for emoji or ANSI box border
    assert any(e in output for e in ["🔎", "💻", "🧠", "\033["])
    # Reset stdout
    monkeypatch.setattr(sys, "stdout", sys.__stdout__)
