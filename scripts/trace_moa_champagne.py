#!/usr/bin/env python3
"""Trace + assert champagne MoA invariants with INFO logs.

Exit 0 only if all checks pass. Useful for CI smoke / docs evidence::

    PYTHONPATH=src python scripts/trace_moa_champagne.py | tee /tmp/moa-trace.log
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from swarm.core.moa.team import (  # noqa: E402
    TeamTask,
    run_moa_consensus,
    run_moa_then_team,
)

FAKES = {
    "analyst": '{"claim":"yes token bucket at edge","confidence":0.9}',
    "critic": '{"claim":"yes token bucket with metrics","confidence":0.85}',
}
Q = "Should we default public APIs to token-bucket rate limiting?"


def check(name: str, cond: bool, detail: str = "") -> tuple[str, bool, str]:
    status = "PASS" if cond else "FAIL"
    print(f"CHECK {status}: {name}" + (f" — {detail}" if detail else ""))
    return name, cond, detail


async def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    checks: list[tuple[str, bool, str]] = []

    print("=" * 60)
    print("consensus_only")
    print("=" * 60)
    a = await run_moa_consensus(
        Q,
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses=FAKES,
    )
    opinions = a.moa_payload.get("opinions") or []
    checks.append(check("consensus_only.mode", a.mode == "consensus_only", a.mode))
    checks.append(check("consensus_only.writes empty", a.writes == [], str(a.writes)))
    checks.append(
        check(
            "consensus_only.panel writes empty",
            (a.moa_payload.get("writes") or []) == [],
        )
    )
    checks.append(
        check(
            "consensus_only.approve-reads",
            {o.get("permission_mode") for o in opinions} == {"approve-reads"},
        )
    )
    checks.append(check("consensus_only.no specialists", a.specialist_results == []))

    print("=" * 60)
    print("consensus_then_team")
    print("=" * 60)
    ws = Path("/tmp/moa-champagne-trace")
    if ws.exists():
        import shutil

        shutil.rmtree(ws)
    b = await run_moa_then_team(
        ws,
        Q,
        specialist_tasks=[
            TeamTask("implementer", "Apply", "decision.md"),
            TeamTask("tester", "Verify", "test_notes.md"),
            TeamTask("docs", "ADR", "docs/ADR.md"),
            TeamTask("researcher", "Scan", "research_notes.md"),
        ],
        seed_files={"notes.txt": "Public API; abuse risk high."},
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses=FAKES,
    )
    checks.append(
        check("consensus_then_team.mode", b.mode == "consensus_then_team", b.mode)
    )
    checks.append(check("consensus_then_team.panel_wrote False", b.panel_wrote is False))
    checks.append(
        check(
            "consensus_then_team.team writes",
            {"decision.md", "test_notes.md", "docs/ADR.md", "research_notes.md"}.issubset(
                set(b.writes)
            ),
            str(b.writes),
        )
    )
    checks.append(
        check(
            "consensus_then_team.specialists ok",
            all(s.ok for s in b.specialist_results),
            str([(s.persona, s.ok) for s in b.specialist_results]),
        )
    )
    decision = (ws / "decision.md").read_text(encoding="utf-8")
    checks.append(
        check(
            "consensus_then_team.decision embeds consensus",
            "token bucket" in decision.lower(),
        )
    )

    failed = [n for n, ok, _ in checks if not ok]
    print("=" * 60)
    print(f"{len(checks) - len(failed)}/{len(checks)} passed")
    if failed:
        print("FAILED:", failed)
        return 1
    print("All champagne invariants held.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
