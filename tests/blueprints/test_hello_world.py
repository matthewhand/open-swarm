import pytest
import asyncio
import re
from src.swarm.blueprints.hello_world.blueprint_hello_world import HelloWorldBlueprint

# REMOVED: trivial or obsolete output structure test.

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

@pytest.mark.asyncio
async def test_hello_world_spinner_and_box_output(capsys):
    import os
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = HelloWorldBlueprint(blueprint_id="test-hello-world")
    messages = [{"role": "user", "content": "Hello, Swarm!"}]
    async for _ in blueprint.run(messages):
        pass
    out = capsys.readouterr().out
    out_clean = strip_ansi(out)
    # Check spinner messages
    assert "Generating." in out_clean
    assert "Generating.." in out_clean
    assert "Generating..." in out_clean
    assert "Running..." in out_clean
    assert "Generating... Taking longer than expected" in out_clean
    # Check emoji box and echo summary
    assert "HelloWorld Echo Spinner" in out_clean
    assert "Echoing: 'Hello, Swarm!'" in out_clean
    assert "👋" in out_clean
    assert "Echo: 'Hello, Swarm!'" in out_clean or "Echo complete for:" in out_clean
