"""Tests for structured MoA proposals and consult_moa tool."""

from __future__ import annotations

import pytest

from swarm.core.moa.orchestrator import default_synthesize
from swarm.core.moa.schema import parse_proposal, score_proposals
from swarm.core.moa.tools import consult_moa
from swarm.core.moa.types import ParticipantOpinion


def test_parse_proposal_free_text_and_json():
    free = parse_proposal("Just use redis.")
    assert free.structured is False
    assert "redis" in free.claim.lower()

    structured = parse_proposal(
        '{"claim": "Use redis with TTL", "confidence": 0.9, "evidence": ["shared cache"]}'
    )
    assert structured.structured is True
    assert structured.claim == "Use redis with TTL"
    assert structured.confidence == 0.9
    assert structured.evidence == ["shared cache"]


def test_score_proposals_prefers_corroborated_structured():
    props = [
        parse_proposal('{"claim": "Use redis", "confidence": 0.8}'),
        parse_proposal('{"claim": "Use redis with TTL", "confidence": 0.7}'),
        parse_proposal("totally unrelated idea about kittens"),
    ]
    ranked = score_proposals(props)
    assert ranked[0][1].structured is True
    assert "redis" in ranked[0][1].claim.lower()


def test_default_synthesize_uses_structured_claims():
    opinions = [
        ParticipantOpinion(
            name="a",
            text='{"claim": "prefer option alpha", "confidence": 0.9}',
            ok=True,
            permission_mode="approve-reads",
        ),
        ParticipantOpinion(
            name="b",
            text='{"claim": "prefer option alpha with metrics", "confidence": 0.8}',
            ok=True,
            permission_mode="approve-reads",
        ),
    ]
    det = default_synthesize("pick", opinions)
    assert "alpha" in det.answer.lower()
    assert det.analysis and det.analysis.get("structured_count") == 2


@pytest.mark.asyncio
async def test_consult_moa_tool_no_act():
    """Orchestrator tool gathers opinions without writing."""
    result = await consult_moa(
        "Should we enable feature flags?",
        ["p1", "p2"],
        backend="fake",
        fake_responses={
            "p1": '{"claim": "yes, gradual rollout", "confidence": 0.85}',
            "p2": '{"claim": "yes, with kill switch", "confidence": 0.8}',
        },
    )
    assert len(result["opinions"]) == 2
    assert result["act"] is None
    assert result["writes"] == []
    assert result["determination"] is not None
    assert all(o["permission_mode"] == "approve-reads" for o in result["opinions"])
