"""Spinner + progressive-output tests for the Geese blueprint.

(The shared display_operation_box rendering contract is covered once in
test_operation_box_shared.py, not duplicated here.)
"""
import pytest

import swarm.blueprints.common.operation_box_utils as opbox_utils
import swarm.blueprints.geese.blueprint_geese as geese_mod
from swarm.blueprints.geese.blueprint_geese import SpinnerState

LONG_WAIT_MSG = "Generating... Taking longer than expected"


def test_geese_spinner_states_enum():
    values = [state.value for state in SpinnerState]
    assert values[:4] == ["Generating.", "Generating..", "Generating...", "Running..."]
    assert SpinnerState.LONG_WAIT.value == LONG_WAIT_MSG


@pytest.fixture
def geese_blueprint_instance():
    GeeseBlueprint = geese_mod.GeeseBlueprint
    config = {
        "llm": {"default": {"provider": "openai", "model": "gpt-mock"}},
        "settings": {"default_llm_profile": "default", "default_markdown_output": True},
        "blueprints": {},
        "llm_profile": "default",
        "mcpServers": {}
    }
    instance = GeeseBlueprint("test_geese", config=config)
    instance.debug = True
    return instance


@pytest.mark.asyncio
async def test_progressive_demo_operation_box(geese_blueprint_instance, monkeypatch):
    blueprint = geese_blueprint_instance
    display_calls = []
    orig_display = opbox_utils.display_operation_box

    def record_display(*args, **kwargs):
        display_calls.append((args, kwargs))
        return orig_display(*args, **kwargs)

    # Patch display_operation_box in BOTH the utility module and the geese
    # blueprint module (geese imports it at module level).
    monkeypatch.setattr(opbox_utils, "display_operation_box", record_display)
    monkeypatch.setattr(geese_mod, "display_operation_box", record_display)

    results = []
    async for r in blueprint.run([{"role": "user", "content": "demo progressive"}]):
        results.append(r)

    # The demo emits progressive operation boxes. Assert the real contract —
    # monotonically increasing result_count/progress_line and a constant
    # total_lines — rather than coupling the count to len(SpinnerState) (which
    # made the test break whenever the demo loop length changed).
    assert display_calls, "expected at least one progressive operation box"
    total_lines_seen = {kwargs["total_lines"] for _, kwargs in display_calls}
    assert len(total_lines_seen) == 1, "total_lines should be constant across the demo"
    for i, (args, kwargs) in enumerate(display_calls, 1):
        assert kwargs["title"] is not None
        assert kwargs["content"] is not None
        assert kwargs["result_count"] == i
        assert kwargs["progress_line"] == i
        assert kwargs.get("op_type", "search") == "search"
    # Run should report progress along the way
    assert any("progress" in str(r).lower() for r in results)
