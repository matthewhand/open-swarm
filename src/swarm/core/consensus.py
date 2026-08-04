"""Reusable consensus service: panel → judge → synthesize.

Extracted from the ``cli_fusion`` blueprint so the same panel→judge→synthesize
loop can be driven from anywhere — a blueprint, the websocket front-end, or as an
``as_tool()`` an orchestrating agent calls *granularly* (escalate one hard
sub-question to a cross-model consensus check). One call = one round; the
master-plan loop stays in the caller.

Consensus-first: when a judge is configured the synthesized answer is grounded in
what the panel agrees on (dissent flagged, not blended away). With no usable
judge the fallback is the **most-corroborated** panel answer — the one sharing the
most content with the others — never simply the longest.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any

from swarm.core.cli_adapter import CliAdapter, CliResult

DEFAULT_MAX_CONCURRENCY = 8

JUDGE_TEMPLATE = """You are the JUDGE in a multi-agent panel. The user's request was:

<request>
{prompt}
</request>

Several independent agents answered it. Compare (do NOT merely concatenate) their answers below.

{panel}

Return ONLY a JSON object with these keys:
- "consensus": list of points the agents agree on
- "contradictions": list of points where they disagree
- "gaps": list of things no agent covered
- "unique_insights": list of valuable points raised by a single agent
- "answer": a single best answer GROUNDED IN THE PANEL'S CONSENSUS — lead with what the agents agree on, and explicitly flag any material disagreement rather than blending it away
- "done": boolean — true if "answer" fully resolves the request, false if another round of work is needed
- "next_step": if not done, one concrete instruction for the next round (else "")
"""


def safe_json(text: str) -> dict[str, Any] | None:
    """Parse a JSON object from CLI output, tolerating surrounding prose."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        try:
            obj = json.loads(text[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


@dataclass
class ConsensusResult:
    """Outcome of one consensus round."""

    answer: str
    analysis: dict[str, Any] | None  # judge JSON: consensus/contradictions/gaps/…/done/next_step
    results: list[CliResult] = field(default_factory=list)  # every panelist (incl. failures)

    @property
    def ok_results(self) -> list[CliResult]:
        return [r for r in self.results if r.ok]

    @property
    def ok(self) -> bool:
        return bool(self.ok_results)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def most_corroborated(results: list[CliResult]) -> str:
    """The panel answer sharing the most content with the others (consensus-first).

    This replaces "pick the longest answer", which rewarded verbosity over
    agreement. With one survivor, that survivor wins by definition.
    """
    ok = [r for r in results if r.ok]
    if not ok:
        return ""
    if len(ok) == 1:
        return ok[0].text
    toks = [(r, _tokens(r.text)) for r in ok]
    def corroboration(item: tuple[CliResult, set[str]]) -> int:
        _, mine = item
        return sum(len(mine & other) for r2, other in toks if r2 is not item[0])
    best, _ = max(toks, key=corroboration)
    return best.text


def synthesize(analysis: dict[str, Any] | None, results: list[CliResult]) -> str:
    """The consensus answer: judge's grounded answer, else most-corroborated."""
    if analysis and isinstance(analysis.get("answer"), str) and analysis["answer"].strip():
        return analysis["answer"].strip()
    return most_corroborated(results)


async def run_consensus(
    prompt: str,
    panel: list[CliAdapter],
    judge: CliAdapter | None = None,
    *,
    workdirs: dict[str, str | None] | None = None,
    child_env: dict[str, str] | None = None,
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
) -> ConsensusResult:
    """Run one panel→judge→synthesize round.

    ``panel`` runs concurrently (bounded by ``max_concurrency``); failures come
    back as not-ok :class:`CliResult` rows (never raises). The judge compares only
    the successful answers. Returns a :class:`ConsensusResult`; when every
    panelist failed, ``answer`` is empty and ``ok`` is False.
    """
    workdirs = workdirs or {}
    sem = asyncio.Semaphore(max(1, max_concurrency))

    async def _one(adapter: CliAdapter) -> CliResult:
        async with sem:
            return await adapter.run(
                prompt, workdir=workdirs.get(adapter.name), extra_env=child_env
            )

    results = list(await asyncio.gather(*(_one(a) for a in panel)))
    ok = [r for r in results if r.ok]
    if not ok:
        return ConsensusResult(answer="", analysis=None, results=results)

    analysis: dict[str, Any] | None = None
    if judge is not None:
        panel_text = "\n\n".join(f"### Agent: {r.name}\n{r.text}" for r in ok)
        jr = await judge.run(
            JUDGE_TEMPLATE.format(prompt=prompt, panel=panel_text),
            workdir=workdirs.get(judge.name),
            extra_env=child_env,
        )
        if jr.ok:
            analysis = safe_json(jr.text)

    return ConsensusResult(answer=synthesize(analysis, ok), analysis=analysis, results=results)
