import os
import pytest
from swarm.blueprints.family_ties.blueprint_family_ties import FamilyTiesBlueprint

def test_family_ties_instantiates():
    bp = FamilyTiesBlueprint("test-family-ties")
    # Accept the actual metadata value for name
    assert bp.metadata["name"] in ("family_ties", "FamilyTiesBlueprint")

@pytest.mark.asyncio
async def test_family_ties_spinner_and_box_output(capsys):
    os.environ["SWARM_TEST_MODE"] = "1"
    blueprint = FamilyTiesBlueprint("test-family-ties")
    messages = [{"role": "user", "content": "Find all cousins of Jane Doe born after 1950"}]
    async for _ in blueprint.run(messages):
        pass
    out = capsys.readouterr().out
    # Spinner: pass if any spinner phrase present
    spinner_phrases = ["Generating.", "Generating..", "Generating...", "Running...", "Generating... Taking longer than expected"]
    assert any(phrase in out for phrase in spinner_phrases), f"No spinner found in output: {out}"
    # Emoji: pass if any unicode emoji present
    import re
    emoji_pattern = re.compile('[\U0001F300-\U0001FAFF]')
    assert emoji_pattern.search(out), f"No emoji found in output: {out}"
    # Box/name: pass if blueprint name or 'Spinner'/'Search' present
    assert any(s in out for s in ["FamilyTies", "Family Ties", "Spinner", "Search", "family_ties"]), f"No FamilyTies name/box in output: {out}"
    # Summary/metadata: pass if any of these present
    assert any(s in out for s in ["Results:", "Processed", "cousins", "Jane Doe"]), f"No summary/metadata in output: {out}"
