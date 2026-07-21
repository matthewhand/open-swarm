"""Optional structured proposal fields for comparable MoA opinions.

Participants may emit free text (always accepted) or a JSON object with
``claim``, ``confidence`` (0..1), and ``evidence`` (list[str]). The orchestrator
can prefer structured fields when present without requiring them.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StructuredProposal:
    claim: str
    confidence: float | None = None
    evidence: list[str] = field(default_factory=list)
    raw_text: str = ""
    structured: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "structured": self.structured,
        }


def parse_proposal(text: str) -> StructuredProposal:
    """Parse free text or a JSON proposal object into StructuredProposal."""
    raw = (text or "").strip()
    if not raw:
        return StructuredProposal(claim="", raw_text=raw, structured=False)

    # Try whole-string JSON, then first {...} block.
    candidates = [raw]
    start, end = raw.find("{"), raw.rfind("}")
    if 0 <= start < end:
        candidates.append(raw[start : end + 1])

    for cand in candidates:
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        claim = str(obj.get("claim") or obj.get("answer") or obj.get("text") or "").strip()
        conf = obj.get("confidence")
        try:
            conf_f = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            conf_f = None
        if conf_f is not None:
            conf_f = max(0.0, min(1.0, conf_f))
        evidence = obj.get("evidence") or obj.get("reasons") or []
        if isinstance(evidence, str):
            evidence = [evidence]
        if not isinstance(evidence, list):
            evidence = []
        evidence = [str(e) for e in evidence]
        if claim:
            return StructuredProposal(
                claim=claim,
                confidence=conf_f,
                evidence=evidence,
                raw_text=raw,
                structured=True,
            )

    return StructuredProposal(claim=raw, raw_text=raw, structured=False)


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def score_proposals(
    proposals: list[StructuredProposal],
    weights: list[float] | None = None,
) -> list[tuple[float, StructuredProposal]]:
    """Rank proposals: structured confidence + token corroboration with peers.

    Optional ``weights`` is parallel to ``proposals`` (default 1.0 each).
    """
    if not proposals:
        return []
    toks = [(p, set(_TOKEN_RE.findall((p.claim or "").lower()))) for p in proposals]
    wlist = list(weights) if weights is not None else [1.0] * len(proposals)
    while len(wlist) < len(proposals):
        wlist.append(1.0)

    scored: list[tuple[float, StructuredProposal]] = []
    for i, (p, mine) in enumerate(toks):
        overlap = sum(len(mine & other) for p2, other in toks if p2 is not p)
        conf = p.confidence if p.confidence is not None else 0.5
        # Structured proposals get a small boost so free-text doesn't dominate by length.
        struct_boost = 0.15 if p.structured else 0.0
        weight = max(0.0, float(wlist[i]))
        score = (float(overlap) + conf + struct_boost) * weight
        scored.append((score, p))
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored
