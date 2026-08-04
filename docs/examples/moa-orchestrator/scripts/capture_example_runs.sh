#!/usr/bin/env bash
# Capture first-class MoA example runs (fake backend) into assets/ + optional SCRATCH.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
ASSETS="$(cd "$(dirname "$0")/.." && pwd)/assets"
SCRATCH="${MOA_EXAMPLE_SCRATCH:-}"
mkdir -p "$ASSETS"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT"

run_cli() {
  .venv/bin/python -c "
from swarm.core.swarm_cli import app
import sys
sys.argv = ['swarm-cli'] + sys.argv[1:]
app()
" "$@"
}

echo "== 01 consensus (run 1) =="
run_cli moa "Should we default public APIs to token-bucket rate limiting?" \
  --backend fake \
  --participants analyst,critic \
  --fake-responses 'analyst={"claim":"yes token bucket at edge","confidence":0.9}||critic={"claim":"yes token bucket with metrics","confidence":0.85}' \
  --json | tee "$ASSETS/01-moa-consensus-fake.json"

echo "== 01 consensus (run 2) =="
run_cli moa "Should we default public APIs to token-bucket rate limiting?" \
  --backend fake \
  --participants analyst,critic \
  --fake-responses 'analyst={"claim":"yes token bucket at edge","confidence":0.9}||critic={"claim":"yes token bucket with metrics","confidence":0.85}' \
  --json | tee "$ASSETS/01-moa-consensus-fake.run2.json"

echo "== 02 orchestrator specialists =="
WS="$ASSETS/example-workspace"
rm -rf "$WS"
mkdir -p "$WS"
.venv/bin/python << PY | tee "$ASSETS/02-moa-orchestrator-specialists.txt"
import asyncio
from pathlib import Path
from swarm.core.moa.agents_orchestrator import SpecialistTask, run_moa_agents_orchestrator

async def main():
    ws = Path(${WS@Q})
    result = await run_moa_agents_orchestrator(
        ws,
        "Should we enable edge rate limiting?",
        specialist_tasks=[
            SpecialistTask("implementer", "Apply decision", "decision.md"),
            SpecialistTask("tester", "Verify", "test_notes.md"),
            SpecialistTask("docs", "Write ADR", "docs/ADR.md"),
        ],
        seed_files={"notes.txt": "Public API; abuse risk high."},
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses={
            "analyst": '{"claim":"yes token bucket","confidence":0.9}',
            "critic": '{"claim":"yes token bucket with metrics","confidence":0.85}',
        },
    )
    print("determination:", result.determination[:400].replace("\n", " / "))
    print("specialists:", [s.persona for s in result.specialist_results])
    print("all_ok:", all(s.ok for s in result.specialist_results))
    print("writes:", result.writes)
    print("reads:", result.reads)

asyncio.run(main())
PY

(
  cd "$WS" && find . -type f | sort
) | tee "$ASSETS/03-workspace-tree.txt"

if [[ -n "$SCRATCH" ]]; then
  mkdir -p "$SCRATCH/moa_example_artifacts"
  cp -a "$ASSETS/01-moa-consensus-fake.json" "$ASSETS/01-moa-consensus-fake.run2.json" \
        "$ASSETS/02-moa-orchestrator-specialists.txt" "$ASSETS/03-workspace-tree.txt" \
        "$SCRATCH/moa_example_artifacts/" 2>/dev/null || true
  cp -a "$ASSETS/01-moa-consensus-fake.json" "$SCRATCH/moa_example_run.log"
  cat "$ASSETS/02-moa-orchestrator-specialists.txt" >> "$SCRATCH/moa_example_run.log"
fi

echo "Assets written under $ASSETS"
