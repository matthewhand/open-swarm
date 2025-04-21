import pytest
from src.swarm.blueprints.whiskeytango_foxtrot.blueprint_whiskeytango_foxtrot import WhiskeyTangoFoxtrotBlueprint
import asyncio
import re

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

@pytest.mark.asyncio
async def test_whiskeytango_foxtrot_smoke():
    blueprint = WhiskeyTangoFoxtrotBlueprint(blueprint_id="test_whiskeytango_foxtrot")
    messages = [{"role": "user", "content": "ping"}]
    async for chunk in blueprint.run(messages):
        assert "messages" in chunk
        break

@pytest.mark.asyncio
async def test_whiskeytango_foxtrot_spinner_and_box(capsys):
    import os
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = WhiskeyTangoFoxtrotBlueprint(blueprint_id="test_whiskeytango_foxtrot")
    messages = [{"role": "user", "content": "ping"}]
    async for _ in blueprint.run(messages):
        pass
    out = capsys.readouterr().out
    out_clean = strip_ansi(out)
    # Check for spinner/box/emoji and summary elements
    assert "Generating." in out_clean
    assert "Generating.." in out_clean
    assert "Generating..." in out_clean
    assert "Running..." in out_clean
    assert "Generating... Taking longer than expected" in out_clean
    assert "✨" in out_clean
    assert "WTF Result" in out_clean or "wtf" in out_clean.lower()
    assert "WTF agent response" in out_clean or "agent response" in out_clean.lower()
    assert "results" in out_clean.lower() or "ping" in out_clean.lower()

# REMOVED: spinner/UX/emoji checks are brittle and not value-adding.
