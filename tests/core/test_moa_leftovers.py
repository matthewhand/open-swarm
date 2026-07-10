"""Leftover MoA features: failover, timeout, vote weights, fingerprint."""

from __future__ import annotations

import asyncio

import pytest

from swarm.core.moa import MoAOrchestrator
from swarm.core.moa.backends import FakeParticipantBackend
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
