#!/usr/bin/env python3
"""Prove a skill works identically across gemini, claude, and grok.

Applies a discovered skill (default: conventional-commit) to the same task on
each installed CLI via the cli_agent blueprint, then checks each output against
the skill's contract. Demonstrates that skills are portable across every CLI in
the fusion catalog.

Run:  DJANGO_DEBUG=true python scripts/prove_skill_across_clis.py [skill] [cli...]
"""
import asyncio
import os
import re
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
os.environ.setdefault("DJANGO_DEBUG", "true")
import django  # noqa: E402

django.setup()

from swarm.blueprints.cli_agent.blueprint_cli_agent import CliAgentBlueprint  # noqa: E402
from swarm.core import cli_catalog, skills  # noqa: E402

SKILL = sys.argv[1] if len(sys.argv) > 1 else "conventional-commit"
CLIS = sys.argv[2:] or ["gemini", "claude", "grok"]
TASK = "Added a retry-with-exponential-backoff wrapper around the S3 upload client."

# The conventional-commit contract: first line is `type(scope?): summary`.
CC_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: .+"
)


async def run_one(cli: str, prompt: str) -> str | None:
    entry = {**cli_catalog.catalog_entry(cli), "timeout": 240}
    bp = CliAgentBlueprint(config={"cli_agents": {cli: entry}, "cli_fusion": {"default_cli": cli}})
    bp.set_params({"cli": cli, "failover": False, "workdir": "/tmp/prove_skill"})
    out = None
    async for c in bp.run([{"role": "user", "content": prompt}], stream=False):
        m = c.get("messages") if isinstance(c, dict) else None
        if m and m[0].get("content") is not None:
            out = m[0]["content"]
    return out


async def main() -> int:
    os.makedirs("/tmp/prove_skill", exist_ok=True)
    catalog = skills.discover_skills()
    if SKILL not in catalog:
        print(f"unknown skill '{SKILL}'; have {sorted(catalog)}", file=sys.stderr)
        return 1
    skill = catalog[SKILL]
    prompt = skills.apply_skill(skill, TASK)
    installed = cli_catalog.installed_catalog_clis()
    clis = [c for c in CLIS if c in installed]

    print(f"Skill: {skill.name}\nTask:  {TASK}\n" + "=" * 78)
    npass = 0
    for cli in clis:
        try:
            out = (await run_one(cli, prompt) or "").strip()
        except Exception as e:  # noqa: BLE001
            print(f"  {cli:8} ERR  {e}")
            continue
        # Agentic CLIs (e.g. grok) may narrate tool use before the answer, so
        # match the contract on ANY line, not just the first.
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        hit = next((ln for ln in lines if CC_RE.match(ln)), None)
        ok = hit is not None
        npass += ok
        print(f"  {cli:8} {'PASS' if ok else 'FAIL'}  {(hit or (lines[0] if lines else ''))[:70]}")
    print("=" * 78)
    print(f"  {npass}/{len(clis)} CLIs honored the '{skill.name}' skill")
    return 0 if npass == len(clis) and clis else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
