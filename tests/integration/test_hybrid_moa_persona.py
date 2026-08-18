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


@pytest.mark.asyncio
async def test_hybrid_default_fakes_json_safe_for_adversarial_question(tmp_path: Path):
    """Omitting moa_fake_responses must use JSON-safe _default_fakes (not quote-broken)."""
    ws = tmp_path / "hybrid_json"
    q = 'Use path C:\\temp\\x and say "yes\\no"?\nSecond line.'
    result = await run_hybrid_scripted(
        ws,
        q,
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        # intentionally no moa_fake_responses → _default_fakes(question, seats)
    )

    assert result.steps[0].persona == "consult_moa"
    assert result.steps[0].ok
    det = result.steps[0].output
    assert "safer option" in det.lower()
    assert "rollback" in det.lower() or "monitoring" in det.lower()
    # Structured panel seats (old string-interp broke JSON → free-text / no [structured])
    assert "[structured]" in det
    assert "Proceed carefully:" not in det
    assert q[:40] not in det.split("\n")[0]

    assert (ws / "moa_determination.md").is_file()
    assert (ws / "decision.md").is_file()
    decision = (ws / "decision.md").read_text(encoding="utf-8")
    assert "safer option" in decision.lower()


@pytest.mark.asyncio
async def test_hybrid_custom_seats_without_explicit_fakes(tmp_path: Path):
    """Custom moa_participants + fake backend must cover seats via _default_fakes."""
    ws = tmp_path / "hybrid_seats"
    seats = ["researcher", "skeptic"]
    result = await run_hybrid_scripted(
        ws,
        "Prefer canary deploys?",
        moa_backend="fake",
        moa_participants=seats,
        # no moa_fake_responses → _default_fakes(question, seats)
    )

    assert result.steps[0].ok
    assert result.steps[1].ok
    # Tool trace records the custom seats (not hardcoded analyst/critic only)
    trace = " ".join(result.steps[0].tool_trace)
    assert "researcher" in trace and "skeptic" in trace
    assert result.agents.get("moa_seats") == seats

    det = result.steps[0].output
    # Hardcoded analyst/critic fakes would yield unknown-participant errors for these seats
    assert "researcher" in det and "skeptic" in det
    assert "[structured]" in det
    assert "unknown participant" not in det.lower()
    assert "safer option" in det.lower()
    assert (ws / "decision.md").is_file()
