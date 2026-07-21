#!/usr/bin/env bash
set -euo pipefail

# smoke_api.sh - Minimal swarm-api smoke test
# - Waits for /v1/models to become available
# - Prints models (via jq if available)
# - Sends a non-streaming /v1/chat/completions request to a simple model
#
# Environment overrides:
#   HOST             Default: localhost
#   PORT             Default: 8000
#   MODEL            Default: echocraft
#   SWARM_API_KEY    Default: dev (if auth enabled)
#   TIMEOUT_SECS     Default: 120 (2 minutes)
#   SLEEP_SECS       Default: 3 (poll interval)
#
# Usage:
#   bash scripts/smoke_api.sh
#   HOST=127.0.0.1 PORT=8001 MODEL=echocraft bash scripts/smoke_api.sh

HOST="${HOST:-localhost}"
PORT="${PORT:-8000}"
MODEL="${MODEL:-echocraft}"
SWARM_API_KEY="${SWARM_API_KEY:-dev}"
TIMEOUT_SECS="${TIMEOUT_SECS:-120}"
SLEEP_SECS="${SLEEP_SECS:-3}"

BASE_URL="http://${HOST}:${PORT}"
MODELS_URL="${BASE_URL}/v1/models"
CHAT_URL="${BASE_URL}/v1/chat/completions"

echo "[smoke] Target: ${BASE_URL}"
echo "[smoke] Waiting for ${MODELS_URL} to become healthy (timeout=${TIMEOUT_SECS}s, interval=${SLEEP_SECS}s)..."

deadline=$(( $(date +%s) + TIMEOUT_SECS ))
attempt=0
while true; do
  attempt=$((attempt + 1))
  if curl -fsS "${MODELS_URL}" >/dev/null 2>&1; then
    echo "[smoke] /v1/models is healthy after ${attempt} attempts."
    break
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "[smoke] ERROR: Timed out waiting for ${MODELS_URL}" >&2
    exit 1
  fi
  sleep "${SLEEP_SECS}"
done

echo "[smoke] Fetching models..."
if command -v jq >/dev/null 2>&1; then
  curl -fsS "${MODELS_URL}" | jq .
else
  curl -fsS "${MODELS_URL}"
fi

echo "[smoke] Sending non-streaming chat completion to model='${MODEL}'..."
payload=$(cat <<JSON
{
  "model": "${MODEL}",
  "messages": [
    {"role": "user", "content": "ping"}
  ]
}
JSON
)

# Authorization header is optional; include if API auth is enabled
auth_header=()
if [ -n "${SWARM_API_KEY:-}" ]; then
  auth_header=(-H "Authorization: Bearer ${SWARM_API_KEY}")
fi

if command -v jq >/dev/null 2>&1; then
  curl -fsS "${CHAT_URL}" \
    -H "Content-Type: application/json" \
    "${auth_header[@]}" \
    -d "${payload}" | jq .
else
  curl -fsS "${CHAT_URL}" \
    -H "Content-Type: application/json" \
    "${auth_header[@]}" \
    -d "${payload}"
fi

echo "[smoke] Completed."