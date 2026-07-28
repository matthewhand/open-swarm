"""Tests: MoA orchestrator in openai-agents mode (consensus then specialists)."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from swarm.core.moa import agents_orchestrator as agents_orch_mod
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

    # Lightweight name roster (no openai-agents construction on scripted path)
    assert result.agents.get("implementer") == "Implementer"
    assert result.agents.get("coordinator") == "Coordinator"
    assert "tester" in result.agents and "docs" in result.agents


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
async def test_consult_moa_panel_uses_configured_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Live coordinator tool must honor moa_backend/participants (not hardcoded fake)."""
    tools = WorkspaceTools(tmp_path / "ws")
    seen: dict[str, object] = {}

    async def fake_consult(
        question,
        participants=None,
        backend=None,
        fake_responses=None,
        **kwargs,
    ):
        seen["question"] = question
        seen["backend"] = backend
        seen["participants"] = list(participants or [])
        seen["fake_responses"] = fake_responses
        return {
            "determination": {"answer": "configured-backend-answer"},
            "opinions": [],
        }

    # Patch both the module used by build_moa_orchestrator_agents and tools.
    monkeypatch.setattr(agents_orch_mod, "consult_moa", fake_consult)
    monkeypatch.setattr("swarm.core.moa.tools.consult_moa", fake_consult)

    agents = build_moa_orchestrator_agents(
        tools,
        moa_backend="grok",
        moa_participants=["seat_a", "seat_b"],
        moa_fake_responses=None,
    )

    panel = next(
        (
            t
            for t in (agents["coordinator"].tools or [])
            if getattr(t, "name", None) == "consult_moa_panel"
        ),
        None,
    )
    assert panel is not None, "coordinator must expose consult_moa_panel"

    out = await panel.on_invoke_tool(None, '{"question":"Should we ship?"}')
    assert "configured-backend-answer" in out
    assert seen.get("backend") == "grok"
    assert seen.get("participants") == ["seat_a", "seat_b"]
    # Helper path stays in sync with the live panel tool.
    helper_out = agents["_tools"]["consult_moa"]("helper path")
    assert "configured-backend-answer" in helper_out
    assert seen.get("backend") == "grok"


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


def test_run_moa_agents_orchestrator_is_scripted_team_path():
    """Executed body is run_moa_then_team — not live Runner / agent-as-tool."""
    src = inspect.getsource(agents_orch_mod.run_moa_agents_orchestrator)
    assert "await run_moa_then_team(" in src
    # Docstring may mention Runner / build_*; body must not call them.
    assert "Runner.run" not in src
    assert "build_moa_orchestrator_agents(" not in src
    # Roster is inspection-only names, not live Agent construction.
    assert "SCRIPTED_ORCHESTRATOR_ROSTER" in src
    # Module must not import/use Runner for the scripted path.
    mod_src = inspect.getsource(agents_orch_mod)
    assert "from agents import Runner" not in mod_src
    assert "Runner.run" not in mod_src


def test_moa_orchestrator_readme_describes_scripted_team_not_model_b():
    """Example README must not claim A-then-B / live agent-as-tool tasking."""
    readme = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "examples"
        / "moa-orchestrator"
        / "README.md"
    )
    text = readme.read_text(encoding="utf-8")
    assert "scripted TeamTask" in text
    assert "run_moa_then_team" in text
    assert "optional/inspection-only" in text or "inspection-only" in text
    # Old incorrect claim (model A then model B agent-as-tool specialists).
    assert "model A then model B" not in text
    assert "agent-as-tool specialists that *may* write" not in text
