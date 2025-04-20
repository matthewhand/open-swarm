import pytest
import time
from swarm.blueprints.zeus.blueprint_zeus import ZeusCoordinatorBlueprint, ZeusSpinner
from swarm.blueprints.common.operation_box_utils import display_operation_box

def test_zeus_spinner_states():
    spinner = ZeusSpinner()
    spinner.start()
    states = []
    for _ in range(6):
        spinner._spin()
        states.append(spinner.current_spinner_state())
    assert states[:3] == ["Generating..", "Generating...", "Running..."]
    # Simulate long wait
    spinner._start_time -= 11
    assert spinner.current_spinner_state() == spinner.LONG_WAIT_MSG

def test_zeus_operation_box_output(capsys):
    spinner = ZeusSpinner()
    spinner.start()
    display_operation_box(
        title="Zeus Test",
        content="Testing operation box",
        spinner_state=spinner.current_spinner_state(),
        emoji="⚡"
    )
    captured = capsys.readouterr()
    assert "Zeus Test" in captured.out
    assert "Testing operation box" in captured.out
    assert "⚡" in captured.out

def test_zeus_assist_box(monkeypatch, capsys):
    blueprint = ZeusCoordinatorBlueprint()
    monkeypatch.setattr(blueprint.spinner, "current_spinner_state", lambda: "Generating...")
    blueprint.assist("hello world")
    captured = capsys.readouterr()
    assert "Zeus Assistance" in captured.out
    assert "hello world" in captured.out

# Edge case: empty input
@pytest.mark.asyncio
async def test_zeus_run_empty(monkeypatch, capsys):
    class DummyAgent:
        async def run(self, messages, **kwargs):
            for i in range(2):
                yield f"step {i}"
    blueprint = ZeusCoordinatorBlueprint()
    monkeypatch.setattr(blueprint, "create_starting_agent", lambda *a, **k: DummyAgent())
    out = []
    async for msg in blueprint.run([{"role": "user", "content": "test"}]):
        out.append(msg)
    captured = capsys.readouterr()
    assert "Zeus Progress" in captured.out
    assert "Zeus Results" in captured.out
    assert out == ["step 0", "step 1"]
