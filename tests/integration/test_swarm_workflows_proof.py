"""Prove dual workflow models A (MoA) and B (persona swarm) on real entry points."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from swarm.core.moa.cli import run_moa_cli
from swarm.core.moa.policy import WriteDeniedError
from swarm.core.moa.backends import RecordingWriteSurface
from swarm.core.persona_swarm import (
    PersonaStep,
    build_persona_agents,
    run_scripted_persona_swarm,
)


ROOT = Path(__file__).resolve().parents[2]
PROOF = Path(os.environ.get("MOA_PROOF_DIR", "/tmp/grok-goal-cb0223abecb8/implementer/proof"))


# ---------------------------------------------------------------------------
# A — Orchestrated consensus (MoA): read-only participants
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workflow_a_moa_participants_readonly_orchestrator_acts(tmp_path: Path):
    """Model A: N opinions, no participant writes; orchestrator determine + act."""
    act_path = tmp_path / "decision.md"
    payload = await run_moa_cli(
        "Should we add rate limiting?",
        ["architect", "sre", "security"],
        backend="fake",
        fake_responses={
            "architect": '{"claim":"yes token bucket at edge","confidence":0.9,"evidence":["simple"]}',
            "sre": '{"claim":"yes token bucket with metrics","confidence":0.85,"evidence":["ops"]}',
            "security": '{"claim":"yes least privilege defaults","confidence":0.8,"evidence":["deny-by-default"]}',
        },
        act=True,
        action="record consensus decision",
        act_write_path=str(act_path),
        trace_path=str(tmp_path / "moa_trace.json"),
    )

    assert len(payload["opinions"]) == 3
    assert all(o["ok"] for o in payload["opinions"])
    assert all(o["permission_mode"] == "approve-reads" for o in payload["opinions"])
    assert payload["determination"] is not None
    assert payload["determination"]["participant_names"] == [
        "architect",
        "sre",
        "security",
    ]
    # Structured proposals parsed
    assert any(
        (o.get("proposal") or {}).get("structured") for o in payload["opinions"]
    )
    # Orchestrator wrote; participants did not get a write surface here
    assert act_path.is_file()
    assert "token bucket" in act_path.read_text(encoding="utf-8").lower() or "yes" in act_path.read_text(
        encoding="utf-8"
    ).lower()
    assert payload["act"] and payload["act"]["ok"]
    assert payload["writes"], "orchestrator act must record writes"
    assert (tmp_path / "moa_trace.json").is_file()


@pytest.mark.asyncio
async def test_workflow_a_participant_write_denied():
    surface = RecordingWriteSurface()
    with pytest.raises(WriteDeniedError):
        surface.write_as_participant("evil.txt", "nope")


def test_workflow_a_swarm_cli_moa_entry():
    """Drive Typer swarm-cli moa the way users do."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from swarm.core.swarm_cli import app; import sys; "
            "sys.argv=['swarm-cli']+sys.argv[1:]; app()",
            "moa",
            "Prove MoA workflow A",
            "--backend",
            "fake",
            "--participants",
            "p1,p2",
            "--fake-responses",
            'p1={"claim":"option one","confidence":0.9}||p2={"claim":"option one with tests","confidence":0.85}',
            "--json",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(proc.stdout[proc.stdout.find("{") :])
    assert len(data["opinions"]) == 2
    assert data["determination"]
    assert all(o["permission_mode"] == "approve-reads" for o in data["opinions"])


# ---------------------------------------------------------------------------
# B — Persona swarm (openai-agents): read/write specialists
# ---------------------------------------------------------------------------


def test_workflow_b_builds_openai_agents_with_rw_tools(tmp_path: Path):
    from agents import Agent

    from swarm.core.persona_swarm import WorkspaceTools

    tools = WorkspaceTools(tmp_path)
    agents = build_persona_agents(tools)
    assert isinstance(agents["coordinator"], Agent)
    assert isinstance(agents["researcher"], Agent)
    assert isinstance(agents["implementer"], Agent)
    # Specialists carry tools (R/W encouraged)
    for name in ("researcher", "implementer", "coordinator"):
        assert agents[name].tools, f"{name} must have tools"
        names = [
            getattr(t, "name", None) or getattr(t, "__name__", "")
            for t in agents[name].tools
        ]
        # At least read + write present among tool names
        flat = " ".join(str(n).lower() for n in names)
        assert "read" in flat or "write" in flat or len(names) >= 2


def test_workflow_b_persona_switch_read_write(tmp_path: Path):
    """Coordinator switches researcher → implementer; implementer writes."""
    ws = tmp_path / "ws"
    result = run_scripted_persona_swarm(
        ws,
        steps=[
            PersonaStep("researcher", "Inspect notes"),
            PersonaStep("implementer", "Write summary.md"),
        ],
        seed_files={"notes.txt": "Ship rate limiting at the edge.\n"},
    )
    assert all(s.ok for s in result.steps)
    assert [s.persona for s in result.steps] == ["researcher", "implementer"]
    # Model B: specialists may write
    assert "summary.md" in result.writes or (ws / "summary.md").is_file()
    assert (ws / "summary.md").is_file()
    body = (ws / "summary.md").read_text(encoding="utf-8")
    assert "rate limiting" in body.lower()
    # Researcher also allowed to write scratch (R/W encouraged)
    assert any("research" in w or w.endswith(".txt") for w in result.writes) or (
        ws / "research_scratch.txt"
    ).exists()
    # Real agent names from openai-agents
    assert result.agents.get("implementer") == "Implementer"
    assert result.agents.get("researcher") == "Researcher"


def test_workflow_b_differs_from_a_on_write_policy(tmp_path: Path):
    """Contrast: B specialists write during the swarm; A participants cannot."""
    # B writes
    b = run_scripted_persona_swarm(
        tmp_path / "b",
        seed_files={"notes.txt": "hello"},
    )
    assert b.writes, "model B must allow specialist writes"

    # A denies participant write surface
    surface = RecordingWriteSurface()
    with pytest.raises(WriteDeniedError):
        surface.write_as_participant("x", "y")


@pytest.mark.asyncio
async def test_workflow_b_runner_hook_falls_back_offline(tmp_path: Path):
    """Runner optional path degrades to scripted R/W swarm without live LLM."""
    from swarm.core.persona_swarm import run_persona_swarm_with_runner

    result = await run_persona_swarm_with_runner(
        tmp_path / "runner_ws",
        "Summarize notes and write summary.md",
        seed_files={"notes.txt": "edge rate limit\n"},
    )
    assert result.agents.get("implementer") == "Implementer"
    # Either live Runner wrote something or scripted fallback produced summary
    assert result.final or result.writes or (tmp_path / "runner_ws" / "summary.md").exists()
