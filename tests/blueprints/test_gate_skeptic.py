"""Gate / Skeptic are role markers only — no execution loop."""

from swarm.blueprints.gate.blueprint_gate import GateBlueprint
from swarm.blueprints.skeptic.blueprint_skeptic import SkepticBlueprint


async def _final(bp, messages=None):
    text = None
    async for chunk in bp.run(messages or []):
        msgs = chunk.get("messages") if isinstance(chunk, dict) else None
        if msgs:
            text = msgs[0]["content"]
    return text


def test_roles():
    assert GateBlueprint.metadata["role"] == "gate"
    assert SkepticBlueprint.metadata["role"] == "skeptic"


async def test_gate_stub_is_one_line():
    text = await _final(GateBlueprint(blueprint_id="gate"))
    assert text == (
        "Gate — call submit_gate_verdict (yes=dangerous / no=safe). Until wired, all approved."
    )
    assert "\n" not in text


async def test_skeptic_stub_is_one_line():
    text = await _final(SkepticBlueprint(blueprint_id="skeptic"))
    assert text == (
        "Skeptic — call submit_skeptic_verdict (pass/fail). If fail, findings go back to retry."
    )
    assert "\n" not in text
