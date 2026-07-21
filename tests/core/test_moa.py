"""TDD tests for Mixture of Agents (MoA).

Exercises the real shipped orchestration path with an injectable participant
backend. No authenticated third-party CLIs required.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest

from swarm.core.moa import (
    PARTICIPANT_PERMISSION_MODES,
    ActResult,
    Determination,
    MoAOrchestrator,
    MoAResult,
    ParticipantOpinion,
    PermissionMode,
    WriteDeniedError,
)
from swarm.core.moa.backends import FakeParticipantBackend, RecordingWriteSurface
from swarm.core.moa.policy import assert_participant_permission, participant_acpx_flags


# ---------------------------------------------------------------------------
# Collect opinions (read-only multi-participant)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_opinions_from_multiple_participants_readonly():
    """N participants each return an opinion; all forced to read-only permission."""
    backend = FakeParticipantBackend(
        {
            "claude": "Use exponential backoff.",
            "codex": "Cap retries at 5 with jitter.",
            "gemini": "Prefer token bucket for rate limits.",
        }
    )
    orch = MoAOrchestrator(backend=backend)

    opinions = await orch.collect_opinions(
        "How should we rate-limit the API?",
        participants=["claude", "codex", "gemini"],
        cwd="/repo",
    )

    assert len(opinions) == 3
    by_name = {o.name: o for o in opinions}
    assert by_name["claude"].ok and "backoff" in by_name["claude"].text
    assert by_name["codex"].ok and "jitter" in by_name["codex"].text
    assert by_name["gemini"].ok and "token bucket" in by_name["gemini"].text

    # Every consult used a read-only permission mode.
    assert len(backend.calls) == 3
    for call in backend.calls:
        assert call["permission"] in PARTICIPANT_PERMISSION_MODES
        assert call["cwd"] == "/repo"
        assert call["prompt"]  # non-empty question framing

    # No write surface activity from participants.
    assert backend.write_surface.writes == []


@pytest.mark.asyncio
async def test_collect_rejects_write_permission_for_participants():
    """Participant path must not accept write / approve-all permission modes."""
    backend = FakeParticipantBackend({"claude": "ok"})
    orch = MoAOrchestrator(backend=backend)

    with pytest.raises(WriteDeniedError):
        await orch.collect_opinions(
            "q",
            participants=["claude"],
            permission=PermissionMode.APPROVE_ALL,  # type: ignore[arg-type]
        )

    assert backend.calls == []
    assert backend.write_surface.writes == []


def test_policy_participant_permission_modes():
    """Policy helpers only allow read-only modes for MoA participants."""
    assert_participant_permission(PermissionMode.APPROVE_READS)
    assert_participant_permission(PermissionMode.DENY_ALL)
    with pytest.raises(WriteDeniedError):
        assert_participant_permission(PermissionMode.APPROVE_ALL)

    flags = participant_acpx_flags(PermissionMode.APPROVE_READS)
    assert "--approve-reads" in flags or any("approve-reads" in f for f in flags)
    assert "--approve-all" not in flags
    assert "exec" in flags  # one-shot


# ---------------------------------------------------------------------------
# Orchestrator-only determination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_determination_is_orchestrator_only_not_a_participant():
    """Consensus determination runs only on the orchestrator path."""
    backend = FakeParticipantBackend(
        {
            "claude": "Answer A: use redis.",
            "codex": "Answer B: use redis with TTL.",
        }
    )
    determine_calls: list[dict[str, Any]] = []

    async def determine_fn(question: str, opinions: list[ParticipantOpinion]) -> Determination:
        determine_calls.append(
            {
                "question": question,
                "names": [o.name for o in opinions],
                "texts": [o.text for o in opinions],
            }
        )
        return Determination(
            answer="Use redis with TTL (synthesized).",
            rationale="Both participants converge on redis; codex adds TTL.",
            participant_names=[o.name for o in opinions if o.ok],
        )

    orch = MoAOrchestrator(backend=backend, determine_fn=determine_fn)
    result = await orch.run(
        "How should we cache sessions?",
        participants=["claude", "codex"],
        act=False,
    )

    assert isinstance(result, MoAResult)
    assert len(result.opinions) == 2
    assert result.determination is not None
    assert "redis" in result.determination.answer.lower()
    assert result.determination.participant_names == ["claude", "codex"]
    assert result.act_result is None

    # Determination invoked exactly once on orchestrator path.
    assert len(determine_calls) == 1
    assert set(determine_calls[0]["names"]) == {"claude", "codex"}

    # Participants were never asked to judge / write.
    for call in backend.calls:
        assert call["permission"] in PARTICIPANT_PERMISSION_MODES
    assert backend.write_surface.writes == []
    # Determine fn is not a participant agent name.
    assert "judge" not in [c["agent"] for c in backend.calls]


@pytest.mark.asyncio
async def test_default_determination_without_custom_fn():
    """Default orchestrator determination synthesizes from opinion texts."""
    backend = FakeParticipantBackend(
        {
            "a": "Prefer option one for simplicity.",
            "b": "Prefer option one with monitoring.",
        }
    )
    orch = MoAOrchestrator(backend=backend)
    result = await orch.run("pick a path", participants=["a", "b"])

    assert result.determination is not None
    assert result.determination.answer
    # Default synthesizer should surface panel content, not invent a blank.
    answer = result.determination.answer.lower()
    assert "option one" in answer or "a:" in answer or "prefer" in answer
    assert set(result.determination.participant_names) == {"a", "b"}


# ---------------------------------------------------------------------------
# Act / write only via orchestrator after determination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_act_only_via_orchestrator_after_determination():
    """Write/impactful ops are denied for participants; allowed only via act after determine."""
    write_surface = RecordingWriteSurface()
    backend = FakeParticipantBackend(
        {"claude": "Propose patch: set timeout=30"},
        write_surface=write_surface,
    )

    act_calls: list[dict[str, Any]] = []

    async def act_fn(determination: Determination, action: str) -> ActResult:
        act_calls.append({"answer": determination.answer, "action": action})
        write_surface.write("config.yaml", "timeout: 30")
        return ActResult(ok=True, detail="wrote config.yaml", side_effects=["config.yaml"])

    orch = MoAOrchestrator(backend=backend, act_fn=act_fn)

    # Participants cannot write even if they try through the shared surface API.
    with pytest.raises(WriteDeniedError):
        backend.write_surface.write_as_participant("evil.txt", "nope")

    result = await orch.run(
        "Set a safe timeout",
        participants=["claude"],
        act=True,
        action="apply recommended timeout",
    )

    assert result.determination is not None
    assert result.act_result is not None
    assert result.act_result.ok
    assert len(act_calls) == 1
    assert write_surface.writes == [("config.yaml", "timeout: 30")]
    # Still only read-only participant calls.
    assert all(c["permission"] in PARTICIPANT_PERMISSION_MODES for c in backend.calls)


@pytest.mark.asyncio
async def test_act_without_prior_determination_raises():
    """Orchestrator.act requires a Determination object (post-determine)."""
    backend = FakeParticipantBackend({"x": "hi"})
    orch = MoAOrchestrator(backend=backend)

    with pytest.raises(ValueError, match="[Dd]etermination"):
        await orch.act(None, action="write something")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_run_act_false_never_writes():
    """act=False leaves write surface untouched even if act_fn is configured."""
    write_surface = RecordingWriteSurface()
    backend = FakeParticipantBackend({"x": "opinion"}, write_surface=write_surface)

    async def act_fn(determination: Determination, action: str) -> ActResult:
        write_surface.write("should_not_exist", "x")
        return ActResult(ok=True, detail="oops")

    orch = MoAOrchestrator(backend=backend, act_fn=act_fn)
    result = await orch.run("q", participants=["x"], act=False)

    assert result.act_result is None
    assert write_surface.writes == []


# ---------------------------------------------------------------------------
# Acpx backend command construction (no live network)
# ---------------------------------------------------------------------------


def test_acpx_backend_builds_readonly_exec_command():
    """Production acpx backend constructs read-only one-shot exec argv."""
    from swarm.core.moa.backends import AcpxParticipantBackend

    be = AcpxParticipantBackend(acpx_bin="acpx")
    argv = be.build_command(
        agent="claude",
        prompt="review auth",
        cwd="/tmp/repo",
        permission=PermissionMode.APPROVE_READS,
        timeout=90,
    )
    assert argv[0] == "acpx"
    assert "--approve-all" not in argv
    assert "--approve-reads" in argv or "--deny-all" in argv
    assert "exec" in argv
    assert "claude" in argv
    assert "--format" in argv
    # quiet or json for machine consumption
    fmt_idx = argv.index("--format")
    assert argv[fmt_idx + 1] in ("quiet", "json")
    assert "--cwd" in argv
    assert "/tmp/repo" in argv
    assert "review auth" in argv


def test_primary_product_name_is_moa_not_fusion():
    """Shipped public exports use MoA naming; fusion/ensemble are not primary."""
    import swarm.core.moa as moa_mod

    assert hasattr(moa_mod, "MoAOrchestrator")
    assert "Mixture of Agents" in (moa_mod.__doc__ or "") or "mixture of agents" in (
        moa_mod.__doc__ or ""
    ).lower()
    # fusion/ensemble must not be the public class names
    assert not hasattr(moa_mod, "CliFusion")
    assert not hasattr(moa_mod, "EnsembleOrchestrator")
