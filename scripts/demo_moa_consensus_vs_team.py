#!/usr/bin/env python3
"""Demo: simple MoA consensus vs consensus-then-team (no openai-agents).

Writes artifacts under docs/examples/moa-consensus-vs-team/assets/ when run
from the repo root (or MOA_DEMO_OUT). Enables INFO logs for champagne tracing.

Usage::

    PYTHONPATH=src python scripts/demo_moa_consensus_vs_team.py
    PYTHONPATH=src python scripts/demo_moa_consensus_vs_team.py --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from swarm.core.moa.team import (  # noqa: E402
    TeamTask,
    format_team_text,
    run_moa_consensus,
    run_moa_then_team,
    team_result_to_payload,
)

Q = "Should we default public APIs to token-bucket rate limiting?"
FAKES = {
    "analyst": '{"claim":"yes token bucket at edge","confidence":0.9}',
    "critic": '{"claim":"yes token bucket with metrics","confidence":0.85}',
}


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(
            __import__("os").environ.get(
                "MOA_DEMO_OUT",
                str(ROOT / "docs/examples/moa-consensus-vs-team/assets"),
            )
        ),
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s %(name)s | %(message)s",
        )

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    print("=== consensus_only ===")
    only = await run_moa_consensus(
        Q,
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses=FAKES,
    )
    only_payload = team_result_to_payload(only, question=Q)
    (out / "05-demo-consensus-only.json").write_text(
        json.dumps(only_payload, indent=2) + "\n", encoding="utf-8"
    )
    print(format_team_text(only_payload))

    print("=== consensus_then_team ===")
    ws = out / "demo-team-workspace"
    if ws.exists():
        import shutil

        shutil.rmtree(ws)
    team = await run_moa_then_team(
        ws,
        Q,
        specialist_tasks=[
            TeamTask("researcher", "Inventory context", "research_notes.md"),
            TeamTask("implementer", "Apply decision", "decision.md"),
            TeamTask("tester", "Verify", "test_notes.md"),
            TeamTask("docs", "Write ADR", "docs/ADR.md"),
        ],
        seed_files={"notes.txt": "Public API; abuse risk high."},
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses=FAKES,
    )
    team_payload = team_result_to_payload(team, question=Q)
    (out / "05-demo-consensus-then-team.json").write_text(
        json.dumps(team_payload, indent=2) + "\n", encoding="utf-8"
    )
    print(format_team_text(team_payload))

    try:
        workspace_display = ws.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        workspace_display = str(ws)

    # Mode ids match result.mode / global MoA (workflow A) — never Path A/B
    # (global B is openai-agents persona swarm).
    contrast = {
        "question": Q,
        "consensus_only": {
            "mode": only.mode,
            "writes": only.writes,
            "specialists": 0,
            "panel_wrote": only.panel_wrote,
            "primary": (only.moa_payload.get("determination") or {})
            .get("analysis", {})
            .get("primary"),
        },
        "consensus_then_team": {
            "mode": team.mode,
            "writes": team.writes,
            "specialists": [s.persona for s in team.specialist_results],
            "panel_wrote": team.panel_wrote,
            "workspace": workspace_display,
        },
        "invariants": {
            "same_panel_permission": all(
                o.get("permission_mode") == "approve-reads"
                for o in (only.moa_payload.get("opinions") or [])
            ),
            # Team-level write surface (consensus-only hard-codes writes=[]).
            "consensus_only_writes_empty": only.writes == [],
            "consensus_then_team_has_writes": "decision.md" in team.writes,
            # Real panel act surface (cli.py payload['writes']); not tautological
            # MoATeamResult.panel_wrote which is always False for this runner.
            "neither_panel_wrote": (
                (only.moa_payload.get("writes") or []) == []
                and (team.moa_payload.get("writes") or []) == []
            ),
        },
    }
    (out / "05-demo-contrast.json").write_text(
        json.dumps(contrast, indent=2) + "\n", encoding="utf-8"
    )
    tree = sorted(p.relative_to(ws).as_posix() for p in ws.rglob("*") if p.is_file())
    (out / "05-demo-workspace-tree.txt").write_text(
        "\n".join(f"./{t}" for t in tree) + "\n", encoding="utf-8"
    )

    ok = all(contrast["invariants"].values())
    print("=== CONTRAST ===")
    print(json.dumps(contrast, indent=2))
    print("invariants_ok:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
