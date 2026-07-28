#!/usr/bin/env bash
# Capture consensus-only vs consensus-then-team (no openai-agents).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
ASSETS="$(cd "$(dirname "$0")/.." && pwd)/assets"
SCRATCH="${MOA_EXAMPLE_SCRATCH:-}"
mkdir -p "$ASSETS"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3

echo "== 01 consensus only =="
"$PY" -c "
from swarm.core.swarm_cli import app
import sys
sys.argv = ['swarm-cli'] + sys.argv[1:]
app()
" moa "Should we default public APIs to token-bucket rate limiting?" \
  --backend fake \
  --participants analyst,critic \
  --fake-responses 'analyst={"claim":"yes token bucket at edge","confidence":0.9}||critic={"claim":"yes token bucket with metrics","confidence":0.85}' \
  --json | tee "$ASSETS/01-consensus-only.json"

echo "== 02 consensus then team =="
WS="$ASSETS/example-workspace"
rm -rf "$WS"
mkdir -p "$WS"
"$PY" << PY | tee "$ASSETS/02-consensus-then-team.txt"
import asyncio
from pathlib import Path
from swarm.core.moa.team import TeamTask, run_moa_then_team

async def main():
    ws = Path(${WS@Q})
    result = await run_moa_then_team(
        ws,
        "Should we enable edge rate limiting?",
        specialist_tasks=[
            TeamTask("implementer", "Apply decision", "decision.md"),
            TeamTask("tester", "Verify", "test_notes.md"),
            TeamTask("docs", "Write ADR", "docs/ADR.md"),
        ],
        seed_files={"notes.txt": "Public API; abuse risk high."},
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses={
            "analyst": '{"claim":"yes token bucket","confidence":0.9}',
            "critic": '{"claim":"yes token bucket with metrics","confidence":0.85}',
        },
    )
    print("mode:", result.mode)
    print("determination:", result.determination[:400].replace("\n", " / "))
    print("specialists:", [s.persona for s in result.specialist_results])
    print("all_ok:", all(s.ok for s in result.specialist_results))
    print("writes:", result.writes)
    print("panel_wrote:", result.panel_wrote)

asyncio.run(main())
PY

(
  cd "$WS" && find . -type f | sort
) | tee "$ASSETS/03-team-workspace-tree.txt"

# Library consensus-only summary for contrast
"$PY" << 'PY' | tee "$ASSETS/01-consensus-only-lib.txt"
import asyncio
from swarm.core.moa.team import run_moa_consensus

async def main():
    r = await run_moa_consensus(
        "Should we default public APIs to token-bucket rate limiting?",
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses={
            "analyst": '{"claim":"yes token bucket at edge","confidence":0.9}',
            "critic": '{"claim":"yes token bucket with metrics","confidence":0.85}',
        },
    )
    print("mode:", r.mode)
    print("writes:", r.writes)
    print("specialists:", len(r.specialist_results))
    print("determination_preview:", r.determination[:200].replace("\n", " / "))

asyncio.run(main())
PY

echo "== 04 CLI --team mode =="
TEAM_WS="$ASSETS/cli-team-workspace"
rm -rf "$TEAM_WS"
"$PY" -c "
from swarm.core.swarm_cli import app
import sys
sys.argv = ['swarm-cli'] + sys.argv[1:]
app()
" moa "Ship rate limiting?" \
  --backend fake \
  --participants analyst,critic \
  --fake-responses 'analyst={"claim":"ship carefully","confidence":0.9}||critic={"claim":"ship carefully with tests","confidence":0.85}' \
  --team --workdir "$TEAM_WS" \
  --team-tasks 'implementer:Apply|tester:Verify|docs:ADR|researcher:Scan' \
  --json 2>/dev/null | tee "$ASSETS/06-cli-team.json"

echo "== demo + champagne trace =="
MOA_DEMO_OUT="$ASSETS" "$PY" "$ROOT/scripts/demo_moa_consensus_vs_team.py" -v \
  2>"$ASSETS/04-trace-run.log" | tee "$ASSETS/05-demo-stdout.txt" || true
# Keep only moa.* lines in the log file if demo wrote mixed stdout
if [[ -f "$ASSETS/04-trace-run.log" ]]; then
  grep -E 'moa\.|INFO ' "$ASSETS/04-trace-run.log" > "$ASSETS/04-trace-run.log.tmp" \
    && mv "$ASSETS/04-trace-run.log.tmp" "$ASSETS/04-trace-run.log" || true
fi
"$PY" "$ROOT/scripts/trace_moa_champagne.py" >> "$ASSETS/04-trace-run.log" 2>&1 || true

if [[ -n "$SCRATCH" ]]; then
  mkdir -p "$SCRATCH/moa_consensus_vs_team"
  cp -a "$ASSETS"/01-* "$ASSETS"/02-* "$ASSETS"/03-* "$ASSETS"/04-* "$ASSETS"/05-* "$ASSETS"/06-* \
    "$SCRATCH/moa_consensus_vs_team/" 2>/dev/null || true
fi

echo "Assets written under $ASSETS"
