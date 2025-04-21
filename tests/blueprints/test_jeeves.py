import pytest
import asyncio
import logging
import re

def strip_ansi(s):
    return re.sub(r'\x1b\[[0-9;]*m', '', s)

try:
    from src.swarm.blueprints.jeeves.blueprint_jeeves import JeevesBlueprint
    import sys
    # print("[DEBUG] sys.path:", sys.path)
    # print("[DEBUG] JeevesBlueprint loaded from:", JeevesBlueprint.__module__)
    # print("[DEBUG] JeevesBlueprint attributes:", dir(JeevesBlueprint))
except ModuleNotFoundError as e:
    pytest.skip(f"Skipping Jeeves tests due to missing dependency: {e}", allow_module_level=True)

@pytest.mark.asyncio
async def test_jeeves_smoke():
    blueprint = JeevesBlueprint(blueprint_id="test_jeeves")
    messages = [{"role": "user", "content": "ping"}]
    # Run the blueprint and ensure it yields a result
    async for chunk in blueprint.run(messages):
        assert "messages" in chunk
        break

@pytest.mark.asyncio
async def test_jeeves_codesearch_ansi_box_and_spinner(capsys):
    import os
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = JeevesBlueprint(blueprint_id="test_jeeves")
    messages = [{"role": "user", "content": "/search foo"}]
    async for _ in blueprint.run(messages, search_mode="code"):
        pass
    out = capsys.readouterr().out
    out_clean = strip_ansi(out)
    assert "Generating." in out_clean
    assert "Generating.." in out_clean
    assert "Generating..." in out_clean
    assert "Running..." in out_clean
    assert "Generating... Taking longer than expected" in out_clean
    assert "Jeeves" in out_clean or "Search" in out_clean
    assert "Matches so far:" in out_clean or "Processed" in out_clean
    assert "Found 3 matches" in out_clean

@pytest.mark.asyncio
async def test_jeeves_semanticsearch_ansi_box_and_spinner(capsys):
    import os
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = JeevesBlueprint(blueprint_id="test_jeeves")
    messages = [{"role": "user", "content": "/semanticsearch bar"}]
    async for _ in blueprint.run(messages, search_mode="semantic"):
        pass
    out = capsys.readouterr().out
    out_clean = strip_ansi(out)
    assert "Semantic Search" in out_clean or "Jeeves Search" in out_clean
    assert "Generating." in out_clean
    assert "Generating.." in out_clean
    assert "Generating..." in out_clean
    assert "Running..." in out_clean
    assert "Generating... Taking longer than expected" in out_clean
    assert "Semantic code search for" in out_clean or "semantic" in out_clean.lower()
    assert "Found 3 matches" in out_clean
    assert "Processed" in out_clean
