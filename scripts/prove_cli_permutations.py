#!/usr/bin/env python3
"""Prove every available CLI works across every framework permutation.

Discovers the installed catalog CLIs and exercises them LIVE through each
blueprint/consensus mode, printing a PASS/FAIL matrix with verbatim output.

Run:  DJANGO_DEBUG=true python scripts/prove_cli_permutations.py
"""
import asyncio
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
os.environ.setdefault("DJANGO_DEBUG", "true")
import django  # noqa: E402

django.setup()

from swarm.core import cli_catalog  # noqa: E402
from swarm.blueprints.cli_agent.blueprint_cli_agent import CliAgentBlueprint  # noqa: E402
from swarm.blueprints.cli_fusion.blueprint_cli_fusion import CliFusionBlueprint  # noqa: E402
from swarm.blueprints.cli_orchestrator.blueprint_cli_orchestrator import CliOrchestratorBlueprint  # noqa: E402
from swarm.blueprints.cli_map.blueprint_cli_map import CliMapBlueprint  # noqa: E402

WD = "/tmp/prove_perms"
os.makedirs(WD, exist_ok=True)
Q = "In one word, what is the capital of France?"

INSTALLED = cli_catalog.installed_catalog_clis()
AGENTS = {n: {**cli_catalog.catalog_entry(n), "timeout": 90} for n in INSTALLED}
PRIMARY = "grok" if "grok" in INSTALLED else (INSTALLED[0] if INSTALLED else None)

results = []  # (permutation, status, verbatim)


def record(name, ans):
    text = (ans or "").strip()
    low = text.lower()
    ok = bool(text) and "all cli" not in low and "unavailable" not in low and "no cli agents" not in low
    results.append((name, "PASS" if ok else "FAIL", text.replace("\n", " ")[:90]))


async def drive(bp, params):
    bp.set_params({**params, "workdir": WD})
    out = None
    async for c in bp.run([{"role": "user", "content": Q}], stream=False):
        m = c.get("messages") if isinstance(c, dict) else None
        if m and m[0].get("content") is not None:
            out = m[0]["content"]
    return out


async def main():
    print(f"Installed CLIs: {INSTALLED}\n")

    # 1. cli_agent — each CLI as a single agent
    for cli in INSTALLED:
        cfg = {"cli_agents": AGENTS, "cli_fusion": {"default_cli": cli}}
        try:
            record(f"cli_agent[{cli}]", await drive(CliAgentBlueprint(config=cfg), {"cli": cli, "failover": False}))
        except Exception as e:  # noqa: BLE001
            results.append((f"cli_agent[{cli}]", "ERR", str(e)[:90]))

    panel = list(INSTALLED)
    fcfg = {"cli_agents": AGENTS,
            "cli_fusion": {"default_cli": PRIMARY, "default_preset": "all",
                           "presets": {"all": {"panel": panel, "judge": PRIMARY}}}}

    # 2. cli_fusion — consensus over the whole panel
    try:
        record("cli_fusion[all]", await drive(CliFusionBlueprint(config=fcfg), {"preset": "all"}))
    except Exception as e:  # noqa: BLE001
        results.append(("cli_fusion[all]", "ERR", str(e)[:90]))

    # 3. cli_orchestrator — router + (forced) escalation
    ocfg = {"cli_agents": AGENTS, "cli_orchestrator": {"router": PRIMARY, "panel": panel, "judge": PRIMARY}}
    try:
        record("cli_orchestrator", await drive(CliOrchestratorBlueprint(config=ocfg),
               {"router": PRIMARY, "panel": panel}))
    except Exception as e:  # noqa: BLE001
        results.append(("cli_orchestrator", "ERR", str(e)[:90]))

    # 4. cli_map — decompose / distribute / reduce
    mcfg = {"cli_agents": AGENTS, "cli_map": {"planner": PRIMARY, "workers": panel, "reducer": PRIMARY}}
    try:
        record("cli_map", await drive(CliMapBlueprint(config=mcfg), {}))
    except Exception as e:  # noqa: BLE001
        results.append(("cli_map", "ERR", str(e)[:90]))

    # 5. self-consensus — same persona x2 (one per CLI)
    for cli in INSTALLED:
        cfg = {"cli_agents": AGENTS, "cli_fusion": {"default_cli": cli}}
        try:
            record(f"self-consensus[{cli}x2]",
                   await drive(CliAgentBlueprint(config=cfg), {"cli": cli, "consensus": 2}))
        except Exception as e:  # noqa: BLE001
            results.append((f"self-consensus[{cli}x2]", "ERR", str(e)[:90]))

    # 6. native best-of-n — for each CLI that has a built-in mode
    for cli in INSTALLED:
        if not cli_catalog.has_native_consensus(cli):
            continue
        entry = {**cli_catalog.with_native_consensus(cli, 2), "timeout": 120}
        cfg = {"cli_agents": {**AGENTS, cli: entry}, "cli_fusion": {"default_cli": cli}}
        try:
            record(f"native-best-of-n[{cli}]",
                   await drive(CliAgentBlueprint(config=cfg), {"cli": cli, "failover": False}))
        except Exception as e:  # noqa: BLE001
            results.append((f"native-best-of-n[{cli}]", "ERR", str(e)[:90]))

    # --- matrix ---
    print("=" * 100)
    print(f"  {'PERMUTATION':32} {'STATUS':6} VERBATIM")
    print("=" * 100)
    npass = 0
    for name, status, text in results:
        if status == "PASS":
            npass += 1
        print(f"  {name:32} {status:6} {text}")
    print("=" * 100)
    print(f"  {npass}/{len(results)} permutations PASS")


if __name__ == "__main__":
    asyncio.run(main())
