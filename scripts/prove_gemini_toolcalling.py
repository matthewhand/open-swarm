#!/usr/bin/env python3
"""Prove a CLI agent does real tool calling through the cli_agent blueprint.

Drives a write-mode CLI (default: gemini) on a task that REQUIRES its file and
shell tools — create a script, run it — then verifies the on-disk result
independently of what the model claims. This is the difference between
one-shot Q&A and genuine agentic tool use.

Run:  DJANGO_DEBUG=true python scripts/prove_gemini_toolcalling.py [cli] [model]
e.g.  python scripts/prove_gemini_toolcalling.py gemini
      python scripts/prove_gemini_toolcalling.py gemini gemini-3-pro-preview
"""
import asyncio
import os
import pathlib
import subprocess
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
os.environ.setdefault("DJANGO_DEBUG", "true")
import django  # noqa: E402

django.setup()

from swarm.core import cli_catalog  # noqa: E402
from swarm.blueprints.cli_agent.blueprint_cli_agent import CliAgentBlueprint  # noqa: E402

CLI = sys.argv[1] if len(sys.argv) > 1 else "gemini"
MODEL = sys.argv[2] if len(sys.argv) > 2 else None
WD = f"/tmp/prove_toolcall_{CLI}"

TASK = (
    "Using your file tools, do all of the following in the current directory: "
    "1) create a file called fib.py that defines fib(n) returning the nth "
    "Fibonacci number (0-indexed, fib(0)=0, fib(1)=1) and prints fib(10); "
    "2) run it with python3 and report the exact stdout."
)


async def main() -> int:
    pathlib.Path(WD).mkdir(parents=True, exist_ok=True)
    fib = pathlib.Path(WD, "fib.py")
    if fib.exists():
        fib.unlink()  # start clean so existence proves the CLI created it

    # Pro/heavy tiers think much longer than flash; give them room.
    entry = (
        cli_catalog.with_model(CLI, MODEL, timeout=600)
        if MODEL
        else {**cli_catalog.catalog_entry(CLI), "timeout": 240}
    )
    cfg = {"cli_agents": {CLI: entry}, "cli_fusion": {"default_cli": CLI}}

    bp = CliAgentBlueprint(config=cfg)
    bp.set_params({"cli": CLI, "failover": False, "workdir": WD})
    out = None
    async for chunk in bp.run([{"role": "user", "content": TASK}], stream=False):
        msgs = chunk.get("messages") if isinstance(chunk, dict) else None
        if msgs and msgs[0].get("content") is not None:
            out = msgs[0]["content"]

    print("=" * 80)
    print(f"{CLI}{' ('+MODEL+')' if MODEL else ''} RESPONSE (verbatim):")
    print("=" * 80)
    print(out)
    print("=" * 80)
    print("INDEPENDENT ON-DISK VERIFICATION:")
    print(f"  fib.py created by the CLI: {fib.exists()}")
    if not fib.exists():
        print("  TOOL-CALLING PROOF: FAIL (no file written)")
        return 1
    print("  --- fib.py ---\n  " + fib.read_text().replace("\n", "\n  "))
    r = subprocess.run(["python3", str(fib)], capture_output=True, text=True, timeout=15)
    ok = r.stdout.strip() == "55"
    print(f"  python3 fib.py stdout: {r.stdout.strip()!r}  (expect '55')")
    print(f"  TOOL-CALLING PROOF: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
