import os
import pytest
from swarm.blueprints.poets.blueprint_poets import PoetsBlueprint

@pytest.mark.asyncio
async def test_poets_spinner_and_box_output(capsys):
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = PoetsBlueprint("test-poets")
    messages = [{"role": "user", "content": "Write a poem about the sea."}]
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
    assert "Poets Spinner" in out or "Poets" in out
    assert "📝" in out
    assert "Results:" in out or "Processed" in out
    assert "poem" in out or "sea" in out
