#!/usr/bin/env python3
"""REQ-79 / #424 — self-update harness (fixture + honest live probe).

Default (CI / Cursor cloud): parse sample ``gh`` stdout, print the operator
checklist, and record why a live in-app PR was **not** opened. Never invents
a pull URL.

Live create is opt-in only: ``SWARM_SELF_UPDATE_LIVE=1`` plus a writable
``gh`` on ``matthewhand/open-swarm``. This script still refuses to invent a
URL when that path is unavailable.

Run:  uv run python scripts/prove_self_update.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from swarm.core.self_update import (  # noqa: E402
    CLOUD_VM_DEVIATION,
    OPERATOR_CHECKLIST,
    TARGET_OWNER_REPO,
    extract_github_pr_url,
    live_pr_capability,
    parse_cli_pr_opened,
)

# Fixture only — a shape ``gh pr create --json`` would print. Not a live PR.
FIXTURE_GH_JSON = (
    '{"url":"https://github.com/matthewhand/open-swarm/pull/416"'
    ',"number":416,"title":"REQ-71 card"}'
)
FIXTURE_GH_LINE = "https://github.com/matthewhand/open-swarm/pull/416"


def main() -> int:
    cap = live_pr_capability()
    json_payload = parse_cli_pr_opened(FIXTURE_GH_JSON, agent_id="cli_agent")
    line_payload = parse_cli_pr_opened(
        f"Opened {FIXTURE_GH_LINE}\n", agent_id="cli_agent"
    )
    fake = extract_github_pr_url("Opened a PR (no url)")

    report = {
        "req": "REQ-79",
        "issue": 424,
        "target": TARGET_OWNER_REPO,
        "fixture_json_ok": bool(json_payload and json_payload.get("url")),
        "fixture_line_ok": bool(line_payload and line_payload.get("url")),
        "invented_url": fake,
        "capability": cap,
        "checklist": list(OPERATOR_CHECKLIST),
        "live_pr_url": cap.get("live_pr_url"),
        "deviation": cap.get("deviation") or (
            None if cap.get("can_live") else CLOUD_VM_DEVIATION
        ),
    }

    print(json.dumps(report, indent=2))
    print()
    print("## Operator checklist")
    for index, step in enumerate(OPERATOR_CHECKLIST, start=1):
        print(f"{index}. {step}")
    print()
    if report["live_pr_url"]:
        print(f"Live PR URL: {report['live_pr_url']}")
    else:
        print("Live PR URL: (none — not invented)")
        if report["deviation"]:
            print(f"Deviation: {report['deviation']}")

    if not report["fixture_json_ok"] or not report["fixture_line_ok"]:
        print("FAIL: fixture gh stdout did not parse to a pr_opened payload", file=sys.stderr)
        return 1
    if report["invented_url"] is not None:
        print("FAIL: harness invented a URL from empty stdout", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
