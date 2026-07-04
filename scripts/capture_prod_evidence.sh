#!/bin/bash
set -euo pipefail
SCRATCH="/tmp/grok-goal-388943eafa57/implementer"
mkdir -p "$SCRATCH"
PORT=8025
echo "=== building local ==="
PORT=$PORT docker compose build --quiet 2>&1 | tail -1 || docker build -t local-open-swarm . --quiet | tail -1
echo "=== starting on $PORT ==="
docker compose down 2>/dev/null || true
PORT=$PORT docker compose up -d
sleep 15
echo "=== /v1/models ==="
curl -s http://localhost:$PORT/v1/models | tee "$SCRATCH/models.json" | python3 -c '
import json,sys
d=json.load(sys.stdin)
print("models:",len(d.get("data",[])))
' 
echo "=== smoke ==="
PORT=$PORT MODEL=suggestion bash scripts/smoke_api.sh | tee "$SCRATCH/smoke.log" | tail -5
echo "=== cli ==="
swarm-cli list --available | tee "$SCRATCH/cli-list.txt" | head -5
SWARM_TEST_MODE=1 swarm-cli install-executable codey | tee "$SCRATCH/cli-install.txt" | tail -2
swarm-cli launch codey --message "evidence test" | tee "$SCRATCH/cli-launch.txt" | head -10
echo "=== secret error ==="
python3 -c '
import os,sys
sys.path.insert(0,"src")
os.environ["DJANGO_DEBUG"]="false"
os.environ.pop("DJANGO_SECRET_KEY",None)
from swarm.utils.env_utils import get_django_secret_key
try: get_django_secret_key()
except Exception as e: print(type(e).__name__, ":", str(e)[:80])
' | tee "$SCRATCH/secret-error.txt"
docker compose down
echo "evidence captured to $SCRATCH"
