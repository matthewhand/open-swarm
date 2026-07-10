"""MoA orchestrator: collect (read-only) → determine → optional act."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from swarm.core.moa.backends import ParticipantBackend
from swarm.core.moa.policy import (
    DEFAULT_PARTICIPANT_PERMISSION,
    WriteDeniedError,
    assert_participant_permission,
)
from swarm.core.moa.types import (
    ActResult,
    Determination,
    ParticipantOpinion,
    PermissionMode,
)

logger = logging.getLogger(__name__)

DetermineFn = Callable[[str, list[ParticipantOpinion]], Awaitable[Determination]]
ActFn = Callable[[Determination, str], Awaitable[ActResult]]


@dataclass
class MoAResult:
    """Full MoA run outcome."""

    opinions: list[ParticipantOpinion]
    determination: Determination | None
    act_result: ActResult | None = None
    question: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def ok_opinions(self) -> list[ParticipantOpinion]:
        return [o for o in self.opinions if o.ok]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def default_synthesize(
    question: str,
    opinions: list[ParticipantOpinion],
    *,
    vote_weights: dict[str, float] | None = None,
) -> Determination:
    """Deterministic orchestrator-side synthesis (no external LLM required).

    Uses optional structured proposals (claim/confidence/evidence) when present,
    otherwise token-overlap corroboration. Optional ``vote_weights`` scale each
    participant's score so answer/rationale/primary stay aligned.
    """
    from swarm.core.moa.schema import parse_proposal, score_proposals

    ok = [o for o in opinions if o.ok and (o.text or "").strip()]
    names = [o.name for o in ok]
    if not ok:
        failed = [o.name for o in opinions if not o.ok]
        return Determination(
            answer="No usable participant opinions.",
            rationale=f"Failed or empty: {failed or 'none'}",
            participant_names=[],
            analysis={"ok_count": 0},
        )
    if len(ok) == 1:
        prop = parse_proposal(ok[0].text)
        return Determination(
            answer=prop.claim or ok[0].text.strip(),
            rationale=f"Single successful participant: {ok[0].name}",
            participant_names=names,
            analysis={
                "ok_count": 1,
                "source": ok[0].name,
                "structured": prop.structured,
            },
        )

    # Prefer structured scoring when any participant emitted JSON proposals.
    props = [parse_proposal(o.text) for o in ok]
    weight_list = None
    if vote_weights:
        weight_list = [float(vote_weights.get(o.name, 1.0)) for o in ok]
    ranked = score_proposals(props, weights=weight_list)
    best_prop = ranked[0][1]
    # Map best claim back to a source opinion name (first match).
    primary_name = ok[0].name
    for o, p in zip(ok, props):
        if p is best_prop or p.claim == best_prop.claim:
            primary_name = o.name
            break

    digest_lines = []
    for o, p in zip(ok, props):
        label = p.claim[:500] if p.claim else o.text.strip()[:500]
        conf = f" conf={p.confidence}" if p.confidence is not None else ""
        struct = " [structured]" if p.structured else ""
        digest_lines.append(f"- {o.name}{struct}{conf}: {label}")

    score_map: dict[str, float] = {}
    for score, prop in ranked:
        for o, p in zip(ok, props):
            if p is prop or p.claim == prop.claim:
                score_map.setdefault(o.name, score)

    weight_note = ", vote-weighted" if vote_weights else ""
    answer = (
        f"{best_prop.claim.strip()}\n\n"
        f"— synthesized by orchestrator from {len(ok)} participants "
        f"(primary: {primary_name}{weight_note})\n\nPanel:\n" + "\n".join(digest_lines)
    )
    rationale = (
        f"Most-corroborated participant opinion from {primary_name}; "
        "panel digest attached for transparency."
    )
    if vote_weights:
        rationale = (
            f"Vote-weighted primary participant: {primary_name} "
            f"(weights={dict(vote_weights)})."
        )
    analysis: dict[str, Any] = {
        "ok_count": len(ok),
        "primary": primary_name,
        "scores": score_map,
        "structured_count": sum(1 for p in props if p.structured),
    }
    if vote_weights:
        analysis["vote_weights"] = dict(vote_weights)
    return Determination(
        answer=answer,
        rationale=rationale,
        participant_names=names,
        analysis=analysis,
    )


async def _default_determine(
    question: str, opinions: list[ParticipantOpinion]
) -> Determination:
    return default_synthesize(question, opinions)


def apply_vote_weights(
    analysis_scores: dict[str, float] | None,
    weights: dict[str, float] | None,
) -> dict[str, float]:
    """Multiply score map by per-participant weights (default weight 1.0)."""
    scores = dict(analysis_scores or {})
    if not weights:
        return scores
    out: dict[str, float] = {}
    for name, score in scores.items():
        w = float(weights.get(name, 1.0))
        out[name] = float(score) * max(0.0, w)
    return out


class MoAOrchestrator:
    """Run Mixture of Agents: read-only collect → orchestrator determine → optional act.

    Participants are consulted only through ``backend`` with a forced read-only
    permission mode. Determination and act never go through the participant
    backend as write-capable agents.
    """

    def __init__(
        self,
        backend: ParticipantBackend,
        *,
        determine_fn: DetermineFn | None = None,
        act_fn: ActFn | None = None,
        participant_permission: PermissionMode | str = DEFAULT_PARTICIPANT_PERMISSION,
        max_concurrency: int = 8,
        per_participant_timeout: float | None = None,
        vote_weights: dict[str, float] | None = None,
        failover: list[str] | None = None,
    ) -> None:
        self.backend = backend
        self.determine_fn: DetermineFn = determine_fn or _default_determine
        self.act_fn = act_fn
        self.participant_permission = assert_participant_permission(
            participant_permission
        )
        self.max_concurrency = max(1, int(max_concurrency))
        # Soft wall-clock budget per participant consult (None = no extra timeout).
        self.per_participant_timeout = per_participant_timeout
        # Optional weights applied during determination scoring (name → weight ≥ 0).
        self.vote_weights = dict(vote_weights or {})
        # Ordered failover chain tried when a primary participant fails.
        self.failover = [str(n) for n in (failover or []) if n]

    async def collect_opinions(
        self,
        question: str,
        participants: list[str],
        *,
        cwd: str | None = None,
        permission: PermissionMode | str | None = None,
    ) -> list[ParticipantOpinion]:
        """Fan out to participants under read-only permission only.

        Failed primaries are replaced by the next unused name from
        ``self.failover`` (if configured). Per-participant timeouts produce an
        unsuccessful opinion rather than aborting the whole panel.
        """
        if permission is not None:
            mode = assert_participant_permission(permission)
        else:
            mode = self.participant_permission

        # Explicit guard: write modes never reach the backend.
        if mode not in (
            PermissionMode.APPROVE_READS.value,
            PermissionMode.DENY_ALL.value,
        ):
            raise WriteDeniedError(
                f"refused non-readonly participant permission: {mode!r}"
            )

        names = [str(n) for n in participants if n]
        if not names:
            return []

        sem = asyncio.Semaphore(self.max_concurrency)
        used: set[str] = set()

        async def _consult(name: str) -> ParticipantOpinion:
            async with sem:
                coro = self.backend.consult(
                    name,
                    question,
                    cwd=cwd,
                    permission=mode,
                )
                if self.per_participant_timeout is None:
                    return await coro
                try:
                    return await asyncio.wait_for(
                        coro, timeout=float(self.per_participant_timeout)
                    )
                except asyncio.TimeoutError:
                    return ParticipantOpinion(
                        name=name,
                        text="",
                        ok=False,
                        permission_mode=mode,
                        error=f"timeout after {self.per_participant_timeout}s",
                    )

        async def _one_with_failover(primary: str) -> ParticipantOpinion:
            chain = [primary] + [f for f in self.failover if f != primary]
            last: ParticipantOpinion | None = None
            for candidate in chain:
                if candidate in used and candidate != primary:
                    continue
                used.add(candidate)
                opinion = await _consult(candidate)
                last = opinion
                if opinion.ok:
                    # Preserve original slot name in meta for tracing failover.
                    if candidate != primary:
                        opinion.meta = {
                            **(opinion.meta or {}),
                            "failover_from": primary,
                            "failover_to": candidate,
                        }
                        opinion = ParticipantOpinion(
                            name=primary,  # keep panel slot id stable
                            text=opinion.text,
                            ok=True,
                            permission_mode=opinion.permission_mode,
                            error=None,
                            meta={
                                **(opinion.meta or {}),
                                "answered_by": candidate,
                                "failover_from": primary,
                            },
                        )
                    return opinion
            return last or ParticipantOpinion(
                name=primary,
                text="",
                ok=False,
                permission_mode=mode,
                error="no candidates",
            )

        return list(await asyncio.gather(*[_one_with_failover(n) for n in names]))

    async def determine(
        self, question: str, opinions: list[ParticipantOpinion]
    ) -> Determination:
        """Orchestrator-only consensus determination (never a participant)."""
        # Pass vote weights into default synthesizer when using the built-in path
        # so answer/rationale/primary stay consistent. Custom determine_fn may
        # ignore weights; we still re-align answer if analysis scores exist.
        if self.determine_fn is _default_determine and self.vote_weights:
            det = default_synthesize(
                question, opinions, vote_weights=self.vote_weights
            )
        else:
            det = await self.determine_fn(question, opinions)
            if self.vote_weights and det.analysis is not None:
                raw_scores = det.analysis.get("scores")
                if isinstance(raw_scores, dict) and raw_scores:
                    weighted = apply_vote_weights(raw_scores, self.vote_weights)
                    primary = max(weighted.items(), key=lambda kv: kv[1])[0]
                    # Rebuild answer/rationale from the weighted primary opinion.
                    by_name = {o.name: o for o in opinions if o.ok}
                    primary_op = by_name.get(primary)
                    if primary_op is not None:
                        from swarm.core.moa.schema import parse_proposal

                        prop = parse_proposal(primary_op.text)
                        claim = (prop.claim or primary_op.text).strip()
                        ok = [o for o in opinions if o.ok and (o.text or "").strip()]
                        digest_lines = []
                        for o in ok:
                            p = parse_proposal(o.text)
                            label = (p.claim or o.text).strip()[:500]
                            conf = f" conf={p.confidence}" if p.confidence is not None else ""
                            struct = " [structured]" if p.structured else ""
                            digest_lines.append(f"- {o.name}{struct}{conf}: {label}")
                        det = Determination(
                            answer=(
                                f"{claim}\n\n"
                                f"— synthesized by orchestrator from {len(ok)} participants "
                                f"(primary: {primary}, vote-weighted)\n\nPanel:\n"
                                + "\n".join(digest_lines)
                            ),
                            rationale=(
                                f"Vote-weighted primary participant: {primary} "
                                f"(weights={dict(self.vote_weights)})."
                            ),
                            participant_names=[o.name for o in ok],
                            analysis={
                                **(det.analysis or {}),
                                "scores": weighted,
                                "vote_weights": dict(self.vote_weights),
                                "primary": primary,
                            },
                        )
                    else:
                        det.analysis = {
                            **det.analysis,
                            "scores": weighted,
                            "vote_weights": dict(self.vote_weights),
                            "primary": primary,
                        }
        return det

    async def act(self, determination: Determination | None, action: str) -> ActResult:
        """Perform an impactful operation only after determination."""
        if determination is None:
            raise ValueError("Determination is required before act")
        if self.act_fn is None:
            raise ValueError("No act_fn configured on MoAOrchestrator")
        return await self.act_fn(determination, action)

    async def run(
        self,
        question: str,
        participants: list[str],
        *,
        cwd: str | None = None,
        act: bool = False,
        action: str | None = None,
        permission: PermissionMode | str | None = None,
    ) -> MoAResult:
        """Full MoA path: collect → determine → optional act."""
        opinions = await self.collect_opinions(
            question, participants, cwd=cwd, permission=permission
        )
        determination = await self.determine(question, opinions)
        act_result: ActResult | None = None
        if act:
            act_result = await self.act(
                determination, action or "apply determination"
            )
        return MoAResult(
            opinions=opinions,
            determination=determination,
            act_result=act_result,
            question=question,
            meta={
                "participants": list(participants),
                "permission": permission or self.participant_permission,
                "act": act,
            },
        )
