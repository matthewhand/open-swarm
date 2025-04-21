import os
import pytest
from swarm.blueprints.omniplex.blueprint_omniplex import OmniplexBlueprint

@pytest.mark.asyncio
async def test_omniplex_spinner_and_box_output(capsys):
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = OmniplexBlueprint("test-omniplex")
    messages = [{"role": "user", "content": "Run npx create-react-app my-app"}]
    async for _ in blueprint.run(messages):
        pass
    out = capsys.readouterr().out
    spinner_phrases = ["Generating.", "Generating..", "Generating...", "Running...", "Generating... Taking longer than expected"]
    assert any(phrase in out for phrase in spinner_phrases), f"No spinner found in output: {out}"
    import re
    emoji_pattern = re.compile('[\U0001F300-\U0001FAFF]')
    assert emoji_pattern.search(out), f"No emoji found in output: {out}"
    assert any(s in out for s in ["Omniplex", "Spinner", "Search"]), f"No Omniplex name/box in output: {out}"
    assert any(s in out for s in ["Results:", "Processed", "npx", "create-react-app"]), f"No summary/metadata in output: {out}"
