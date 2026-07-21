"""Hybrid champagne: persona coordinator consults MoA then implementer writes."""

from __future__ import annotations

from pathlib import Path

import pytest

from swarm.core.persona_swarm import build_persona_agents, run_hybrid_scripted, WorkspaceTools


@pytest.mark.asyncio
async def test_hybrid_moa_then_implementer_writes(tmp_path: Path):
    """A (read-only MoA) then B (implementer write) — no participant file writes."""
    ws = tmp_path / "hybrid"
    result = await run_hybrid_scripted(
        ws,
        "Should we enable edge rate limiting?",
        seed_files={"notes.txt": "API is public; abuse risk is high.\n"},
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses={
            "analyst": '{"claim":"yes token bucket","confidence":0.9}',
            "critic": '{"claim":"yes token bucket with metrics","confidence":0.85}',
        },
    )

    assert len(result.steps) == 2
    assert result.steps[0].persona == "consult_moa"
    assert result.steps[0].ok
    assert "token bucket" in result.steps[0].output.lower()
    assert result.steps[1].persona == "implementer"
    assert result.steps[1].ok

    # MoA determination recorded + implementer decision written (B-side only)
    assert (ws / "moa_determination.md").is_file()
    assert (ws / "decision.md").is_file()
    decision = (ws / "decision.md").read_text(encoding="utf-8")
    assert "token bucket" in decision.lower()
    assert "MoA" in decision or "moa" in decision.lower()

    # Writes are coordinator/implementer paths, not panelist names
    assert "decision.md" in result.writes
    assert "moa_determination.md" in result.writes
    # Seed notes must still exist (panel did not clobber workspace as writers)
    assert (ws / "notes.txt").read_text(encoding="utf-8").startswith("API is public")


def test_coordinator_agent_has_consult_moa_tool(tmp_path: Path):
    """openai-agents coordinator is wired with consult_moa_panel tool."""
    tools = WorkspaceTools(tmp_path / "ws")
    agents = build_persona_agents(tools)
    coord = agents["coordinator"]
    names = []
    for t in getattr(coord, "tools", None) or []:
        names.append(
            getattr(t, "name", None)
            or getattr(t, "__name__", None)
            or type(t).__name__
        )
    flat = " ".join(str(n).lower() for n in names)
    assert "consult_moa" in flat or "moa" in flat
    # Sync helper available for scripted/hybrid use
    assert callable(agents["_tools"].get("consult_moa"))
