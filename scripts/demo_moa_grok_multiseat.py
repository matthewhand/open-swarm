#!/usr/bin/env python3
"""Live multi-seat Grok MoA demo (or fake fallback). Writes an artifact directory."""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = Path(
    __import__("os").environ.get(
        "MOA_DEMO_OUT",
        str(ROOT / "docs" / "proofs" / "moa_grok_multiseat"),
    )
)


async def main() -> int:
    from swarm.core.moa import GrokParticipantBackend
    from swarm.core.moa.cli import run_moa_cli

    OUT.mkdir(parents=True, exist_ok=True)
    question = (
        "Should open-swarm default public APIs to token-bucket rate limiting "
        "at the edge? Answer with a short recommendation."
    )
    seats = ["analyst", "critic"]
    grok = GrokParticipantBackend()
    use_grok = grok.is_available()
    backend = "grok" if use_grok else "fake"
    fake = None
    if not use_grok:
        fake = {
            "analyst": (
                '{"claim":"Yes — token bucket at the edge with clear defaults",'
                '"confidence":0.88,"evidence":["abuse risk"]}'
            ),
            "critic": (
                '{"claim":"Yes — token bucket plus metrics and a kill switch",'
                '"confidence":0.84,"evidence":["operability"]}'
            ),
        }

    payload = await run_moa_cli(
        question,
        seats,
        backend=backend,
        fake_responses=fake,
        cwd=str(ROOT),
        timeout=120.0,
        act=False,
        trace_path=str(OUT / "trace.json"),
    )

    report = {
        "when": datetime.now(timezone.utc).isoformat(),
        "backend": backend,
        "grok_available": use_grok,
        "question": question,
        "seats": seats,
        "opinions": payload.get("opinions"),
        "determination": payload.get("determination"),
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    det = (payload.get("determination") or {}).get("answer") or ""
    (OUT / "determination.md").write_text(
        f"# MoA multi-seat demo\n\nBackend: `{backend}`\n\n## Question\n{question}\n\n"
        f"## Determination\n\n{det}\n",
        encoding="utf-8",
    )
    print(json.dumps({"backend": backend, "ok": bool(det), "out": str(OUT)}, indent=2))
    print("--- determination preview ---")
    print(det[:800] if det else "(empty)")
    return 0 if det else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
