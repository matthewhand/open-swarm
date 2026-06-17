#!/usr/bin/env python3
"""Show blueprint-intent -> backend mapping, live.

For several desired profiles (intelligence / speed+cost / balanced), resolve the
best-matching installed CLI by its capability traits, then actually run a prompt
on the resolved CLI to confirm the decoupling works against live inference.

Run:  DJANGO_DEBUG=true python scripts/demo_inference_profile.py
"""
import asyncio
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
os.environ.setdefault("DJANGO_DEBUG", "true")
import django  # noqa: E402

django.setup()

from swarm.blueprints.cli_agent.blueprint_cli_agent import CliAgentBlueprint  # noqa: E402
from swarm.blueprints.common import cli_fusion_support as support  # noqa: E402
from swarm.core import cli_catalog  # noqa: E402

# Targets name only the axes the blueprint cares about (distance-from-ideal):
PROFILES = [
    ("deep reasoning",  {"intelligence": 1.0}),
    ("fast & cheap",    {"speed": 1.0, "cost": 1.0}),
    ("balanced",        {"intelligence": 0.6, "speed": 0.6, "cost": 0.6}),
]
Q = "In one word, what is the capital of France?"


async def main() -> int:
    installed = cli_catalog.installed_catalog_clis()
    cfg = {"cli_agents": {n: {**cli_catalog.catalog_entry(n), "timeout": 90} for n in installed}}
    registry = support.build_registry(cfg)
    os.makedirs("/tmp/demo_profile", exist_ok=True)

    print(f"Installed CLIs + default traits (intelligence/speed/cost):")
    for n in installed:
        t = cli_catalog.cli_traits(n) or {}
        print(f"  {n:9} {t.get('intelligence',0):.2f} / {t.get('speed',0):.2f} / {t.get('cost',0):.2f}")
    print("=" * 78)
    print(f"  {'DESIRED PROFILE':16} {'-> RESOLVED CLI':16} LIVE ANSWER")
    print("=" * 78)
    npass = 0
    for label, prof in PROFILES:
        picked = support.resolve_by_profile(prof, cfg, registry)
        bp = CliAgentBlueprint(config=cfg)
        bp.set_params({"profile": prof, "failover": False, "workdir": "/tmp/demo_profile"})
        out = None
        async for c in bp.run([{"role": "user", "content": Q}], stream=False):
            m = c.get("messages") if isinstance(c, dict) else None
            if m and m[0].get("content") is not None:
                out = m[0]["content"]
        ans = (out or "").strip().splitlines()[-1][:34] if out else "(none)"
        ok = bool(out) and "paris" in (out or "").lower()
        npass += ok
        print(f"  {label:16} -> {picked or '(none)':14} {ans}")
    print("=" * 78)
    print(f"  {npass}/{len(PROFILES)} resolved-CLI runs answered correctly")
    return 0 if npass == len(PROFILES) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
