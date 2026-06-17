#!/usr/bin/env python3
"""Generate a README-worthy 3-CLI consensus example.

Runs a real question through a panel of three agentic CLIs (gemini, claude,
grok) in parallel, has a judge compare them, and renders a markdown artifact
that shows *each agent's individual contribution* alongside the judge's
analysis and the final synthesized answer — so a reader can see exactly how
each CLI shaped the result.

Run:  DJANGO_DEBUG=true python scripts/demo_consensus.py "<question>" [out.md]
"""
import asyncio
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
os.environ.setdefault("DJANGO_DEBUG", "true")
import django  # noqa: E402

django.setup()

from swarm.core import cli_catalog  # noqa: E402
from swarm.core.consensus import run_consensus  # noqa: E402
from swarm.blueprints.common import cli_fusion_support as support  # noqa: E402

PANEL = ["gemini", "claude", "grok"]
JUDGE = "grok"
DEFAULT_Q = (
    "A REST API endpoint that lists orders has gotten slow (~3s) as the orders "
    "table grew past 5M rows. Give the single highest-leverage fix and why."
)


def _entry(name: str) -> dict:
    return {**cli_catalog.catalog_entry(name), "timeout": 240}


async def main() -> int:
    question = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_Q
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    workdir = "/tmp/demo_consensus"
    os.makedirs(workdir, exist_ok=True)

    config = {
        "cli_agents": {n: _entry(n) for n in PANEL},
        "cli_fusion": {"default_cli": JUDGE},
    }
    registry = support.build_registry(config)
    available = registry.available()
    panel_names = [n for n in PANEL if n in available]
    if len(panel_names) < 2:
        print(f"Need >=2 of {PANEL} installed; have {panel_names}", file=sys.stderr)
        return 1

    panel = registry.resolve_panel(panel_names)
    judge = registry.get(JUDGE) if JUDGE in available else None
    workdirs = {n: workdir for n in panel_names + [JUDGE]}

    cons = await run_consensus(question, panel, judge, workdirs=workdirs)

    # --- render README-worthy markdown ---
    L: list[str] = []
    L.append(f"### Consensus across {len(panel_names)} CLIs — {', '.join(panel_names)}\n")
    L.append(f"**Question**\n\n> {question}\n")
    L.append("#### Each agent's individual contribution\n")
    for r in cons.results:
        status = "✅" if r.ok else f"❌ ({r.error})"
        L.append(f"<details><summary><b>{r.name}</b> {status} · {r.duration:.1f}s</summary>\n")
        L.append(f"\n{r.text.strip() if r.ok else r.error}\n\n</details>\n")

    a = cons.analysis or {}
    if a:
        L.append("\n#### Judge's analysis (`%s`)\n" % JUDGE)
        for key, label in [
            ("consensus", "Where the agents agree"),
            ("contradictions", "Where they disagree"),
            ("unique_insights", "Unique insights (raised by one agent)"),
            ("gaps", "Gaps (no agent covered)"),
        ]:
            vals = a.get(key)
            if vals:
                L.append(f"\n**{label}:**\n")
                items = vals if isinstance(vals, list) else [vals]
                for it in items:
                    L.append(f"- {it}")
    L.append("\n#### Final synthesized answer\n")
    L.append(f"\n{cons.answer.strip()}\n")

    md = "\n".join(L)
    print(md)
    if out_path:
        with open(out_path, "w") as f:
            f.write(md + "\n")
        print(f"\n[written to {out_path}]", file=sys.stderr)
    return 0 if cons.ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
