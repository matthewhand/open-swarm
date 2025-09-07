import inspect
import time

import pytest
from swarm.blueprints.common.operation_box_utils import display_operation_box
from swarm.blueprints.zeus.blueprint_zeus import (  # Import ZeusSpinner for FRAMES
    ZeusCoordinatorBlueprint,
    ZeusSpinner,
)


def test_zeus_spinner_states():
    spinner = ZeusSpinner()
    spinner.start()
    states = []
    for _ in range(6):
        spinner._spin()
        states.append(spinner.current_spinner_state())
    spinner.stop()

    assert "Generating." in states or "Generating.." in states

    spinner._start_time = time.time() - (ZeusSpinner.SLOW_THRESHOLD + 1)
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
    spinner.stop()
    captured = capsys.readouterr()
    assert "Zeus Test" in captured.out
    assert "Testing operation box" in captured.out
    assert "⚡" in captured.out

def test_zeus_assist_box(monkeypatch, capsys):
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    blueprint = ZeusCoordinatorBlueprint(debug=False)
    monkeypatch.setattr(blueprint.cli_spinner, "current_spinner_state", lambda: "Generating...")
    blueprint.assist("hello world")
    captured = capsys.readouterr()
    assert "Zeus Assistance" in captured.out
    assert "hello world" in captured.out

@pytest.mark.asyncio
async def test_zeus_run_empty(monkeypatch):
    class DummyAgent:
        async def run(self, messages, **kwargs):
            yield {"messages": [{"role": "assistant", "content": "step 0"}]}
            yield {"messages": [{"role": "assistant", "content": "step 1"}]}

    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    blueprint = ZeusCoordinatorBlueprint(debug=False)

    dummy_agent_instance = DummyAgent()
    assert inspect.isasyncgenfunction(dummy_agent_instance.run), "Test's DummyAgent.run is not an async generator function!"

    monkeypatch.setattr(blueprint, "create_starting_agent", lambda *a, **k: dummy_agent_instance)

    collected_outputs = []
    async for msg_dict in blueprint.run([{"role": "user", "content": "test"}]):
        if msg_dict and "messages" in msg_dict and msg_dict["messages"]:
            collected_outputs.append(msg_dict["messages"][0]["content"])

    assert len(collected_outputs) >= 3, f"Expected at least 3 messages (spinner + 2 steps), got: {len(collected_outputs)}. Outputs: {collected_outputs}"

    initial_spinner_msg = collected_outputs[0]
    # Corrected assertion: Check if it's one of the known frames or contains "Generating"
    assert initial_spinner_msg in ZeusSpinner.FRAMES or "Generating" in initial_spinner_msg, \
           f"Expected a Zeus spinner message in first output. Got: '{initial_spinner_msg}'. Expected one of {ZeusSpinner.FRAMES} or containing 'Generating'. All: {collected_outputs}"

    step_0_found = any("Zeus Result" in output and "step 0" in output for output in collected_outputs[1:])
    step_1_found = any("Zeus Result" in output and "step 1" in output for output in collected_outputs[1:])

    assert step_0_found, f"Expected 'Zeus Result' box containing 'step 0'. Outputs after spinner: {collected_outputs[1:]}"
    assert step_1_found, f"Expected 'Zeus Result' box containing 'step 1'. Outputs after spinner: {collected_outputs[1:]}"
