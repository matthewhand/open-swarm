#!/usr/bin/env bash
# Render Mermaid diagrams from README to SVG (optional; needs npx @mermaid-js/mermaid-cli).
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

extract "### Architecture flowchart" "diagram-architecture"
extract "### 2.1 Collect" "diagram-collect"
extract "### 2.2 Orchestrator" "diagram-specialists"

if command -v npx >/dev/null 2>&1; then
  for name in diagram-architecture diagram-collect diagram-specialists; do
    npx --yes @mermaid-js/mermaid-cli@11 \
      -i "$ASSETS/${name}.mmd" -o "$ASSETS/${name}.svg" -b transparent || true
  done
else
  echo "npx not available; left .mmd sources only"
fi

# Terminal-style PNG "screenshot" of consensus JSON
if [[ -f "$ASSETS/01-moa-consensus-fake.json" ]]; then
  python3 - <<PY || true
from pathlib import Path
assets = Path(r"$ASSETS")
src = assets / "01-moa-consensus-fake.json"
out = assets / "01-moa-consensus-fake.png"
text = src.read_text()[:3500]
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("no pillow")
lines = text.splitlines()
line_h = 16
pad = 24
w = 920
h = min(900, pad * 2 + line_h * (len(lines) + 2))
img = Image.new("RGB", (w, h), "#1e1e1e")
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 12
    )
except Exception:
    font = ImageFont.load_default()
draw.text(
    (pad, 10),
    "$ swarm-cli moa … --backend fake --json",
    fill="#6a9955",
    font=font,
)
y = pad + 8
for line in lines:
    draw.text((pad, y), line[:120], fill="#d4d4d4", font=font)
    y += line_h
    if y > h - pad:
        break
img.save(out)
print(f"wrote {out}")
PY
  if [[ ! -f "$ASSETS/01-moa-consensus-fake.png" ]] && command -v convert >/dev/null 2>&1; then
    convert -background '#1e1e1e' -fill '#d4d4d4' -font DejaVu-Sans-Mono -pointsize 11 \
      label:@"$ASSETS/01-moa-consensus-fake.json" \
      "$ASSETS/01-moa-consensus-fake.png" 2>/dev/null || \
      echo "convert failed; skip png"
  fi
fi

echo "Done rendering under $ASSETS"
