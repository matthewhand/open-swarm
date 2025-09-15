import io  # <--- ADDED IMPORT IO

import pytest
from rich.panel import Panel
from swarm.core.output_utils import print_operation_box as display_operation_box_core

# Define JEEVES_SPINNER_STATES if not easily importable or use a generic list
JEEVES_SPINNER_STATES = ["Polishing the silver", "Generating.", "Generating..", "Generating...", "Running..."]

def fake_progressive_tool():
    matches = []
    total = 3
    for i in range(1, total + 1):
        matches.append(f"match{i}")
        yield {
            "matches": list(matches),
            "progress": i,
            "total": total,
            "status": "running" if i < total else "complete"
        }

@pytest.mark.timeout(2)
def test_display_operation_box_progress(monkeypatch):
    calls = []
    def fake_console_print(panel_obj):
        calls.append(panel_obj)

    from rich.console import Console
    mock_console_instance = Console(file=io.StringIO(), width=120, color_system=None, legacy_windows=True)
    mock_console_instance.print = fake_console_print

    # This monkeypatch ensures that if print_operation_box_core creates its own Console,
    # it gets our mocked one.
    monkeypatch.setattr("swarm.core.output_utils.Console", lambda: mock_console_instance)

    for idx, update in enumerate(fake_progressive_tool()):
        display_operation_box_core(
            title="Progressive Test",
            content=f"Matches so far: {len(update['matches'])}",
            result_count=len(update['matches']),
            params={"pattern": "foo|bar|baz"},
            progress_line=update["progress"],
            total_lines=update["total"],
            spinner_state=JEEVES_SPINNER_STATES[idx % len(JEEVES_SPINNER_STATES)],
            emoji="🤖",
            style="info",
            console=mock_console_instance
        )

    assert len(calls) == 3, f"Expected 3 calls to console.print, got {len(calls)}"
    for i, panel_obj in enumerate(calls):
        assert isinstance(panel_obj, Panel), "Object printed should be a Rich Panel"

        panel_content_str = ""
        if hasattr(panel_obj, 'renderable') and panel_obj.renderable:
            if hasattr(panel_obj.renderable, 'plain'):
                panel_content_str = panel_obj.renderable.plain
            else:
                panel_content_str = str(panel_obj.renderable)

        panel_title_str = str(panel_obj.title) if hasattr(panel_obj, 'title') else ""

        assert f"Results: {i+1}" in panel_content_str
        assert f"Progress: {i+1}/3" in panel_content_str
        assert "🤖" in panel_title_str, f"Emoji not found in title. Title: '{panel_title_str}', Content: '{panel_content_str}'"
        expected_spinner = JEEVES_SPINNER_STATES[i % len(JEEVES_SPINNER_STATES)]
        assert f"[{expected_spinner}]" in panel_content_str
