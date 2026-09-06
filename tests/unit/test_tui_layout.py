"""ASCII chrome for the Wave 0 TUI scaffold."""

from swarm.tui.client import RailSeat
from swarm.tui.layout import render_scaffold


def test_render_scaffold_marks_selected_and_placeholder():
    text = render_scaffold(
        [
            RailSeat(id="support", name="Support", kind="api", source="blueprints"),
            RailSeat(id="grok", name="Grok", kind="cli", source="cli-agents"),
        ],
        selected_id="grok",
        base_url="http://127.0.0.1:8000",
    )
    assert "AGENTS" in text
    assert "> Grok" in text
    assert "Support" in text
    assert "placeholder" in text.lower()
    assert "http://127.0.0.1:8000" in text
    assert "8001" not in text


def test_render_scaffold_empty_rail_is_honest():
    text = render_scaffold([], base_url="http://127.0.0.1:8000")
    assert "none" in text.lower()
    assert "placeholder" in text.lower()
