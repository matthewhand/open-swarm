#!/usr/bin/env python3
"""Prove a skill's bundled executable asset is staged and run by a CLI.

Uses the counting-lines skill (ships count.py). We write a file with a known
number of non-blank lines into the workdir, then ask a write-mode CLI — via the
`skill=` param — for the exact count. The skill stages count.py automatically;
the CLI must EXECUTE it (not guess) to get the right answer, which we verify
independently. Proves skills + tool calling compose.

Run:  DJANGO_DEBUG=true python scripts/prove_skill_asset_toolcall.py [cli...]
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
from swarm.core import cli_catalog  # noqa: E402

CLIS = sys.argv[1:] or ["grok", "gemini", "claude"]
# 12 lines, 7 non-blank — blank lines make eyeballing error-prone, so a correct
# answer is strong evidence the CLI actually ran count.py.
TARGET = "alpha\n\nbravo\ncharlie\n\n\ndelta\necho\n\nfoxtrot\n\ngolf\n"
EXPECTED = 7


async def run_one(cli: str, wd: str) -> str | None:
    entry = {**cli_catalog.catalog_entry(cli), "timeout": 240}
    bp = CliAgentBlueprint(config={"cli_agents": {cli: entry}, "cli_fusion": {"default_cli": cli}})
    bp.set_params({"cli": cli, "failover": False, "skill": "counting-lines", "workdir": wd})
    out = None
    task = "How many non-blank lines are in target.txt? Give the exact number."
    async for c in bp.run([{"role": "user", "content": task}], stream=False):
        m = c.get("messages") if isinstance(c, dict) else None
        if m and m[0].get("content") is not None:
            out = m[0]["content"]
    return out


async def main() -> int:
    installed = cli_catalog.installed_catalog_clis()
    clis = [c for c in CLIS if c in installed]
    print(f"Skill: counting-lines (ships count.py)  ·  target.txt non-blank lines = {EXPECTED}")
    print("=" * 78)
    npass = 0
    for cli in clis:
        wd = f"/tmp/prove_asset_{cli}"
        os.makedirs(wd, exist_ok=True)
        with open(os.path.join(wd, "target.txt"), "w") as f:
            f.write(TARGET)
        try:
            out = (await run_one(cli, wd) or "").strip()
        except Exception as e:  # noqa: BLE001
            print(f"  {cli:8} ERR  {e}")
            continue
        staged = os.path.isfile(os.path.join(wd, "count.py"))
        nums = re.findall(r"\b\d+\b", out)
        ok = staged and str(EXPECTED) in nums
        npass += ok
        print(f"  {cli:8} {'PASS' if ok else 'FAIL'}  staged={staged} answer~={nums[:3]}  "
              f"{out.splitlines()[-1][:50] if out else ''}")
    print("=" * 78)
    print(f"  {npass}/{len(clis)} CLIs staged + executed the bundled count.py")
    return 0 if clis and npass == len(clis) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
