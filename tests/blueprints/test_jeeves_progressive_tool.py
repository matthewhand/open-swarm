import pytest
from swarm.core.output_utils import print_operation_box as display_operation_box

# Use a local spinner states definition matching the new JeevesSpinner standard
JEEVES_SPINNER_STATES = [
    "Generating.",
    "Generating..",
    "Generating...",
    "Running..."
]

def fake_progressive_tool():
    # Simulate a progressive tool yielding 3 updates and a final done
    yield {"matches": ["foo"], "progress": 1, "total": 3, "truncated": False, "done": False}
    yield {"matches": ["foo", "bar"], "progress": 2, "total": 3, "truncated": False, "done": False}
    yield {"matches": ["foo", "bar", "baz"], "progress": 3, "total": 3, "truncated": False, "done": True}

@pytest.mark.timeout(2)
def test_display_operation_box_progress(monkeypatch):
    calls = []
    def fake_print(self, panel, *args, **kwargs):
        calls.append(panel)
    monkeypatch.setattr("rich.console.Console.print", fake_print)
    for idx, update in enumerate(fake_progressive_tool()):
        display_operation_box(
            title="Progressive Test",
            content=f"Matches so far: {len(update['matches'])}",
            result_count=len(update['matches']),
            params={"pattern": "foo|bar|baz"},
            progress_line=update["progress"],
            total_lines=update["total"],
            spinner_state=JEEVES_SPINNER_STATES[idx % len(JEEVES_SPINNER_STATES)],
            emoji="🤖"
        )
    assert len(calls) == 3
    for i, panel in enumerate(calls):
        # Panel.renderable is the box content
        content = str(panel.renderable)
        assert f"Results: {i+1}" in content
        assert f"Progress: {i+1}/3" in content
        assert "🤖" in content
