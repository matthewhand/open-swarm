#!/usr/bin/env bash
# Render Mermaid diagrams from README to SVG.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
ASSETS="$DIR/assets"
mkdir -p "$ASSETS"

extract() {
  local id="$1"
  local out="$2"
  python3 - <<PY
from pathlib import Path
text = Path("$DIR/README.md").read_text()
marker = "$id"
idx = text.find(marker)
if idx < 0:
    raise SystemExit(f"marker not found: {marker}")
rest = text[idx:]
start = rest.find("\`\`\`mermaid")
end = rest.find("\`\`\`", start + 10)
if start < 0 or end < 0:
    raise SystemExit("mermaid fence not found after: $id")
body = rest[start + len("\`\`\`mermaid"):end].strip() + "\n"
Path("$ASSETS/$out.mmd").write_text(body)
print(f"wrote $ASSETS/$out.mmd ({len(body)} bytes)")
PY
}

extract "### 2.1 Path A" "diagram-consensus-only"
extract "### 2.2 Path B" "diagram-then-team"

if command -v npx >/dev/null 2>&1; then
  for name in diagram-consensus-only diagram-then-team; do
    npx --yes @mermaid-js/mermaid-cli@11 \
      -i "$ASSETS/${name}.mmd" -o "$ASSETS/${name}.svg" -b transparent || true
  done
else
  echo "npx not available; left .mmd sources only"
fi

echo "Done rendering under $ASSETS"
