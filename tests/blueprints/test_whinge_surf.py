import pytest
from src.swarm.blueprints.whinge_surf.blueprint_whinge_surf import WhingeSurfBlueprint
import asyncio

@pytest.mark.asyncio
async def test_whinge_surf_spinner_and_box(capsys):
    blueprint = WhingeSurfBlueprint(blueprint_id="test_whinge_surf")
    messages = [{"role": "user", "content": "Test spinner and box."}]
    # Run the blueprint and capture output
    async for _ in blueprint.run(messages, force_slow_spinner=True):
        pass
    out = capsys.readouterr().out
    print('---DEBUG OUTPUT START---')
    print(repr(out))
    print('---DEBUG OUTPUT END---')
    # Check spinner messages
    assert "Generating." in out
    assert "Generating... Taking longer than expected" in out
    # Check ANSI/emoji box (rely on visible elements)
    assert "🌊" in out
    assert "Blueprint scaffold / UX demonstration" in out
    assert "Results: 1" in out
    assert "WhingeSurf is under construction" in out
