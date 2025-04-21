import pytest
from src.swarm.blueprints.whinge_surf.blueprint_whinge_surf import WhingeSurfBlueprint
import asyncio
import os

@pytest.mark.asyncio
async def test_whinge_surf_spinner_and_box(capsys):
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = WhingeSurfBlueprint(blueprint_id="test_whinge_surf")
    messages = [{"role": "user", "content": "Test spinner and box."}]
    # Run the blueprint and capture output
    async for _ in blueprint.run(messages, force_slow_spinner=True):
        pass
    out = capsys.readouterr().out
    # print('---DEBUG OUTPUT START---')
    print(repr(out))
    # print('---DEBUG OUTPUT END---')
    # Check spinner messages
    assert "Generating." in out
    assert "Generating.." in out
    assert "Generating..." in out
    assert "Running..." in out
    assert "Generating... Taking longer than expected" in out
    # Check ANSI/emoji box (rely on visible elements)
    assert "🌊" in out
    assert "WhingeSurf Search" in out
    assert "Results: 1" in out or "Results: 2" in out
    assert "Processed" in out

@pytest.mark.asyncio
async def test_whinge_surf_subprocess_launch_and_status():
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = WhingeSurfBlueprint(blueprint_id="test_whinge_surf")
    # Launch subprocess
    messages = [{"role": "user", "content": "!run something"}]
    result = None
    async for out in blueprint.run(messages):
        result = out
    assert result is not None
    content = result["messages"][0]["content"]
    assert "Launched subprocess" in content
    # Check status (should be running, then finished)
    messages = [{"role": "user", "content": "!status test-proc-id-1234"}]
    async for out in blueprint.run(messages):
        content = out["messages"][0]["content"]
        assert "Subprocess status" in content
