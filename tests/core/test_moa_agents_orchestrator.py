"""Tests: MoA orchestrator in openai-agents mode (consensus then specialists)."""

from __future__ import annotations

from pathlib import Path

import pytest

from swarm.core.moa.agents_orchestrator import (
    SPECIALIST_PURPOSES,
    SpecialistTask,
    build_moa_orchestrator_agents,
    run_moa_agents_orchestrator,
)
from swarm.core.persona_swarm import WorkspaceTools


@pytest.mark.asyncio
async def test_orchestrator_moa_then_multi_specialists(tmp_path: Path):
    """Panel is read-only; implementer + tester + docs write purpose files."""
    ws = tmp_path / "orch"
    result = await run_moa_agents_orchestrator(
        ws,
        "Should we enable edge rate limiting?",
        specialist_tasks=[
            SpecialistTask("implementer", "Write the decision", "decision.md"),
            SpecialistTask("tester", "Draft verification", "test_notes.md"),
            SpecialistTask("docs", "Write ADR", "docs/ADR.md"),
        ],
        seed_files={"notes.txt": "Public API; abuse risk high."},
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses={
            "analyst": '{"claim":"yes token bucket","confidence":0.9}',
            "critic": '{"claim":"yes token bucket with metrics","confidence":0.85}',
        },
    )

    assert "token bucket" in result.determination.lower()
    assert len(result.specialist_results) == 3
    assert all(s.ok for s in result.specialist_results)
    assert {s.persona for s in result.specialist_results} == {
        "implementer",
        "tester",
        "docs",
    }

    assert (ws / "moa_determination.md").is_file()
    assert (ws / "decision.md").is_file()
    assert (ws / "test_notes.md").is_file()
    assert (ws / "docs" / "ADR.md").is_file()

    # Writes are specialist/orchestrator artifacts only
    assert "decision.md" in result.writes
    assert "test_notes.md" in result.writes
    # Seed notes untouched content-wise
    assert "abuse risk" in (ws / "notes.txt").read_text(encoding="utf-8")


def test_build_orchestrator_agents_has_consult_and_specialists(tmp_path: Path):
    tools = WorkspaceTools(tmp_path / "ws")
    agents = build_moa_orchestrator_agents(tools, moa_backend="fake")
    assert "coordinator" in agents
    assert "implementer" in agents
    assert "tester" in agents or "docs" in agents
    assert callable(agents["_tools"].get("consult_moa"))
    coord = agents["coordinator"]
    instr = (coord.instructions or "").lower()
    assert "read-only" in instr or "consult_moa" in instr


@pytest.mark.asyncio
async def test_unknown_specialist_purpose_fails_soft(tmp_path: Path):
    result = await run_moa_agents_orchestrator(
        tmp_path / "u",
        "q",
        specialist_tasks=[SpecialistTask("hacker", "pwn")],
        moa_backend="fake",
        moa_fake_responses={
            "analyst": '{"claim":"no","confidence":0.5}',
            "critic": '{"claim":"no","confidence":0.5}',
        },
    )
    assert result.specialist_results
    assert not result.specialist_results[0].ok
    assert "unknown" in result.specialist_results[0].output.lower()


def test_specialist_purposes_documented():
    assert "implementer" in SPECIALIST_PURPOSES
    assert "tester" in SPECIALIST_PURPOSES
