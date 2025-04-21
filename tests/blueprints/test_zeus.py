import os
import pytest
from swarm.blueprints.zeus.blueprint_zeus import ZeusBlueprint

@pytest.mark.asyncio
async def test_zeus_spinner_and_box_output(capsys):
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = ZeusBlueprint("test-zeus")
    messages = [{"role": "user", "content": "Design and implement a login system."}]
    async for _ in blueprint.run(messages):
        pass
    out = capsys.readouterr().out
    # Check spinner messages
    assert "Generating." in out
    assert "Generating.." in out
    assert "Generating..." in out
    assert "Running..." in out
    assert "Generating... Taking longer than expected" in out
    # Check emoji box and summary
    assert "Zeus Search" in out or "Zeus" in out
    assert "⚡" in out or "🔨" in out or "🧠" in out
    assert "Results:" in out or "Processed" in out
    assert "login system" in out or "agent" in out
    # Check all spinner states
    assert "Generating." in out
    assert "Generating.." in out
    assert "Generating..." in out
    assert "Running..." in out
    assert "Generating... Taking longer than expected" in out
    # Check all emojis
    assert "⚡" in out or "🔨" in out or "🧠" in out
    # Check summary
    assert "Results:" in out or "Processed" in out
    assert "login system" in out or "agent" in out
