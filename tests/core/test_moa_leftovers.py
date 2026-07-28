"""Leftover MoA features: failover, timeout, vote weights, fingerprint."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from swarm.core.moa import MoAOrchestrator
from swarm.core.moa.backends import (
    AcpxParticipantBackend,
    FakeParticipantBackend,
    GrokParticipantBackend,
)
from swarm.core.moa.orchestrator import apply_vote_weights
from swarm.core.moa.types import ParticipantOpinion
from swarm.views.chat_views import backend_fingerprint


@pytest.mark.asyncio
async def test_failover_replaces_failed_primary():
    backend = FakeParticipantBackend(
        {"backup": "Recovered answer from backup."},
        errors={"primary": "boom"},
    )
    orch = MoAOrchestrator(backend=backend, failover=["backup"])
    opinions = await orch.collect_opinions("q", ["primary"])
    assert len(opinions) == 1
    assert opinions[0].ok
    assert opinions[0].name == "primary"  # slot stable
    assert (opinions[0].meta or {}).get("answered_by") == "backup"
    assert "Recovered" in opinions[0].text


@pytest.mark.asyncio
async def test_per_participant_timeout():
    class SlowBackend:
        async def consult(self, agent, prompt, *, cwd=None, permission="approve-reads"):
            await asyncio.sleep(2.0)
            return ParticipantOpinion(
                name=agent, text="late", ok=True, permission_mode=permission
            )

    orch = MoAOrchestrator(backend=SlowBackend(), per_participant_timeout=0.05)
    opinions = await orch.collect_opinions("q", ["slow"])
    assert len(opinions) == 1
    assert not opinions[0].ok
    assert "timeout" in (opinions[0].error or "").lower()


class _HangingProc:
    """Subprocess mock that blocks in communicate until kill()."""

    def __init__(self) -> None:
        self.returncode = None
        self._done = asyncio.Event()
        self.kill_calls = 0

    async def communicate(self):
        await self._done.wait()
        return (b"", b"")

    def kill(self) -> None:
        self.kill_calls += 1
        self.returncode = -9
        self._done.set()

    async def wait(self):
        await self._done.wait()
        return self.returncode


@pytest.mark.asyncio
async def test_grok_killed_when_orchestrator_timeout_cancels_consult():
    """Outer per_participant_timeout must kill grok children (not only backend timeout)."""
    be = GrokParticipantBackend(grok_bin="grok", default_timeout=180.0)
    proc = _HangingProc()

    with patch(
        "asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=proc),
    ):
        orch = MoAOrchestrator(backend=be, per_participant_timeout=0.05)
        opinions = await orch.collect_opinions("q", ["seat"])

    assert len(opinions) == 1
    assert not opinions[0].ok
    assert "timeout" in (opinions[0].error or "").lower()
    assert proc.kill_calls >= 1


@pytest.mark.asyncio
async def test_acpx_killed_when_orchestrator_timeout_cancels_consult():
    """Outer per_participant_timeout must kill acpx children (CLI --timeout alone is not enough)."""
    be = AcpxParticipantBackend(acpx_bin="acpx", default_timeout=300.0)
    proc = _HangingProc()

    with patch(
        "asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=proc),
    ):
        orch = MoAOrchestrator(backend=be, per_participant_timeout=0.05)
        opinions = await orch.collect_opinions("q", ["claude"])

    assert len(opinions) == 1
    assert not opinions[0].ok
    assert "timeout" in (opinions[0].error or "").lower()
    assert proc.kill_calls >= 1


@pytest.mark.asyncio
async def test_grok_backend_timeout_still_kills_process():
    """Backend-local default_timeout path continues to kill + report timeout."""
    be = GrokParticipantBackend(grok_bin="grok", default_timeout=0.05)
    proc = _HangingProc()

    with patch(
        "asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=proc),
    ):
        opinion = await be.consult("seat", "prompt")

    assert not opinion.ok
    assert "timed out" in (opinion.error or "").lower()
    assert proc.kill_calls >= 1


@pytest.mark.asyncio
async def test_vote_weights_reweight_primary():
    backend = FakeParticipantBackend(
        {
            "low": '{"claim":"option A shared words", "confidence":0.5}',
            "high": '{"claim":"option A shared words", "confidence":0.5}',
        }
    )
    orch = MoAOrchestrator(
        backend=backend,
        vote_weights={"high": 10.0, "low": 0.1},
    )
    result = await orch.run("pick", ["low", "high"])
    assert result.determination is not None
    analysis = result.determination.analysis or {}
    assert analysis.get("vote_weights")
    scores = analysis.get("scores") or {}
    assert scores.get("high", 0) >= scores.get("low", 0)


def test_apply_vote_weights_helper():
    out = apply_vote_weights({"a": 2.0, "b": 3.0}, {"a": 2.0})
    assert out["a"] == 4.0
    assert out["b"] == 3.0


def test_backend_fingerprint_moa_panel():
    fp = backend_fingerprint(
        "moa",
        {"backends": ["architect", "sre"], "moa": True},
    )
    assert fp == "moa:architect+sre"
    assert backend_fingerprint("moa", None) == "moa"
