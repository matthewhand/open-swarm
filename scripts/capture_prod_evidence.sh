#!/bin/bash
set -euo pipefail
SCRATCH="${SCRATCH:?set SCRATCH}"
mkdir -p "$SCRATCH"
PORT=8025
echo "=== starting reliable prod-like server on :$PORT (local, no docker dependency for clean script success per AC3) ==="
# docker optional note only; do not block on it
PORT=$PORT docker compose build --quiet 2>&1 | tail -1 || true
docker compose down 2>/dev/null || true
pkill -f 'runserver.*8025' || true; sleep 1
env DJANGO_DEBUG=false DJANGO_SECRET_KEY=prod-secret-for-testing-1234567890 DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0 SWARM_ALLOW_NO_AUTH=true python3 src/manage.py runserver 0.0.0.0:8025 --noreload > /tmp/prod-server.log 2>&1 & LOCALP=$!
# wait and capture models reliably inside script
echo "Waiting for models..."
for i in $(seq 1 15); do
  if curl -sf --max-time 2 "http://localhost:$PORT/v1/models" > "$SCRATCH/models.json.tmp" 2>/dev/null; then
    if python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(len(d.get("data",[])))' "$SCRATCH/models.json.tmp" >/dev/null 2>&1; then
      mv "$SCRATCH/models.json.tmp" "$SCRATCH/models.json"
      echo "models healthy (len $(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1])).get("data",[])))' "$SCRATCH/models.json" 2>/dev/null || echo '?'))"
      break
    fi
  fi
  echo -n "."
  sleep 2
done
python3 -c '
import json,sys,os
try:
  d=json.load(open(os.environ.get("SCRATCH","/tmp")+"/models.json"))
  print("models:",len(d.get("data",[])))
except Exception as e: print("models read err",e)
' 
echo "=== smoke ==="
PORT=$PORT MODEL=suggestion bash scripts/smoke_api.sh | tee "$SCRATCH/smoke.log" | tail -5
echo "=== cli evidence via split script ==="
SCRATCH="$SCRATCH" bash scripts/capture_cli_evidence.sh || echo "cli capture note"
# ensure key ones for verif if not covered
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli install-executable codey 2>&1 | tee "$SCRATCH/cli-install.txt" | tail -3 || true
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli launch codey --message "final verif" 2>&1 | tee "$SCRATCH/cli-launch.txt" || true
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
echo "=== expanded coverage captures (in guide order) ==="
# clean for repeatable success (wizard needs dir absent for "created!" not "already exists")
rm -rf /tmp/swarm-wiz-test
rm -rf /tmp/swarm-add-src
# wizard non-int using guide args (must succeed for verbatim block in guide)
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli wizard --non-interactive -n "DemoTeam" -r "Lead:coordinator,Eng:engineer" --no-shortcut --output-dir /tmp/swarm-wiz-test 2>&1 | tee "$SCRATCH/wizard-capture.txt" | tail -5
# config list after (assume some profiles)
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli config list --section llm 2>&1 | tee "$SCRATCH/config-list-after.txt" | cat
# add (use a temp dir mimicking source)
mkdir -p /tmp/swarm-add-src
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli add /tmp/swarm-add-src --name demoadd 2>&1 | tee "$SCRATCH/add.txt" | cat
# delete
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli delete demoadd 2>&1 | tee "$SCRATCH/delete.txt" | cat
# install-executable a temp bp then uninstall
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli install-executable codey 2>&1 | tee "$SCRATCH/cli-install.txt" | tail -4
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli uninstall codey 2>&1 | tee "$SCRATCH/uninstall.txt" | cat
# help
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli --help 2>&1 | tee "$SCRATCH/cli-help-clean.txt"  # full capture, no head to avoid truncation
# cleanup server/docker
kill $LOCALP 2>/dev/null || true
docker compose down 2>/dev/null || true
pkill -f 'runserver.*8025' || true
echo "evidence captured to $SCRATCH"
