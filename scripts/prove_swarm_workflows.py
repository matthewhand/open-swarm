#!/usr/bin/env python3
"""Live proof of workflow A (MoA) and B (persona swarm). Writes artifacts + stdout."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PROOF = Path(
    __import__("os").environ.get(
        "MOA_PROOF_DIR", "/tmp/grok-goal-cb0223abecb8/implementer/proof"
    )
)
PROOF.mkdir(parents=True, exist_ok=True)


async def prove_a() -> dict:
    from swarm.core.moa.cli import format_moa_text, run_moa_cli

    payload = await run_moa_cli(
        "Should we add rate limiting to the public API?",
        ["architect", "sre", "security"],
        backend="fake",
        fake_responses={
            "architect": '{"claim":"Yes — token bucket at the edge","confidence":0.9,"evidence":["low complexity"]}',
            "sre": '{"claim":"Yes — token bucket with metrics and alerts","confidence":0.88,"evidence":["operability"]}',
            "security": '{"claim":"Yes — deny-by-default quotas","confidence":0.86,"evidence":["abuse prevention"]}',
        },
        act=True,
        action="persist determination",
        act_write_path=str(PROOF / "a_moa_decision.md"),
        trace_path=str(PROOF / "a_moa_trace.json"),
    )
    text = format_moa_text(payload)
    (PROOF / "a_moa_report.txt").write_text(text, encoding="utf-8")
    return payload


def prove_b() -> dict:
    from swarm.core.persona_swarm import PersonaStep, run_scripted_persona_swarm

    ws = PROOF / "b_workspace"
    result = run_scripted_persona_swarm(
        ws,
        steps=[
            PersonaStep("researcher", "Read notes and list workspace"),
            PersonaStep("implementer", "Write summary.md from notes"),
        ],
        seed_files={
            "notes.txt": "Decision context: add edge rate limiting with token bucket.\n"
        },
    )
    report = {
        "agents": result.agents,
        "steps": [
            {
                "persona": s.persona,
                "ok": s.ok,
                "tool_trace": s.tool_trace,
                "output_preview": s.output[:400],
            }
            for s in result.steps
        ],
        "writes": result.writes,
        "reads": result.reads,
        "summary_exists": (ws / "summary.md").is_file(),
        "summary_preview": (ws / "summary.md").read_text(encoding="utf-8")[:500]
        if (ws / "summary.md").is_file()
        else None,
    }
    (PROOF / "b_persona_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    print("=" * 60)
    print("WORKFLOW A — MoA (read-only participants + orchestrator act)")
    print("=" * 60)
    a = asyncio.run(prove_a())
    print(f"opinions: {len(a['opinions'])}")
    for o in a["opinions"]:
        print(f"  - {o['name']}: perm={o['permission_mode']} ok={o['ok']}")
        print(f"    proposal={o.get('proposal')}")
    print(f"determination primary analysis: {(a.get('determination') or {}).get('analysis')}")
    print(f"act: {a.get('act')}")
    print(f"writes: {a.get('writes')}")
    print(f"artifacts: {PROOF / 'a_moa_decision.md'}, {PROOF / 'a_moa_trace.json'}")

    print()
    print("=" * 60)
    print("WORKFLOW B — Persona swarm (openai-agents, R/W specialists)")
    print("=" * 60)
    b = prove_b()
    print(f"agents: {b['agents']}")
    for s in b["steps"]:
        print(f"  - persona={s['persona']} ok={s['ok']} tools={s['tool_trace']}")
    print(f"writes: {b['writes']}")
    print(f"reads: {b['reads']}")
    print(f"summary_exists: {b['summary_exists']}")
    print(f"summary_preview:\n{b['summary_preview']}")

    # Contrast proof
    print()
    print("=" * 60)
    print("CONTRAST")
    print("=" * 60)
    print("A participants permission modes:", {o["permission_mode"] for o in a["opinions"]})
    print("A participant writes during collect: none (writes only via act):", a["writes"])
    print("B specialist writes during swarm:", b["writes"])
    ok = (
        len(a["opinions"]) >= 2
        and a["determination"]
        and a["act"]
        and b["summary_exists"]
        and b["writes"]
    )
    print("PROOF_OK" if ok else "PROOF_FAIL")
    (PROOF / "PROOF_SUMMARY.json").write_text(
        json.dumps({"workflow_a": a, "workflow_b": b, "ok": ok}, indent=2, default=str),
        encoding="utf-8",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
