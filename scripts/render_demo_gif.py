#!/usr/bin/env python3
"""Render docs/demo/cli-and-api.gif — the README terminal demo.

The GIF shows the core differentiator: ONE blueprint (zeus) runs as a local
CLI command AND answers via the OpenAI-compatible HTTP API.

Honesty rule: every output line shown in the animation is a genuine capture
(see docs/demo/captures/raw_*.txt for the untrimmed originals). Only the
command typing is animated; output is replayed verbatim. The single `…` line
marks where a contiguous block of capture lines was elided for space.

Scene files (docs/demo/captures/scene{1,2,3}.txt) use a simple format:
  - lines starting with "$ "  -> typed at the prompt (char-by-char animation)
  - every other line          -> printed output (revealed in blocks)

Regenerate the captures with:
  SWARM_TEST_MODE=1 uv run swarm-cli list
  SWARM_TEST_MODE=1 uv run python -m swarm.blueprints.zeus.zeus_cli \
      --message "Plan a release: tests, changelog, tag"
  SWARM_TEST_MODE=1 DJANGO_DEBUG=true uv run python manage.py runserver 8447 --noreload &
  curl -s localhost:8447/v1/models | jq -c '[.data[].id]'
  curl -s localhost:8447/v1/chat/completions -H 'Content-Type: application/json' \
      -d '{"model":"zeus","stream":true,"messages":[{"role":"user","content":"Plan a release: tests, changelog, tag"}]}'

Then render:  uv run python scripts/render_demo_gif.py
Requires Pillow (`uv pip install pillow`) and DejaVu Sans Mono (Linux default).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPTURES = REPO_ROOT / "docs" / "demo" / "captures"
OUT_PATH = REPO_ROOT / "docs" / "demo" / "cli-and-api.gif"

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
]

WIDTH = 800
FONT_SIZE = 13
LINE_H = 18
PAD_X = 14
PAD_Y = 10
TITLEBAR_H = 28
ROWS = 19  # visible terminal rows

BG = (24, 25, 33)
TITLEBAR_BG = (40, 42, 54)
FG_OUTPUT = (205, 207, 214)
FG_COMMAND = (245, 245, 245)
FG_PROMPT = (80, 250, 123)
FG_COMMENT = (124, 131, 155)
FG_TITLE = (160, 165, 180)
TRAFFIC = [(255, 95, 86), (255, 189, 46), (39, 201, 63)]
TITLE = "open-swarm demo — SWARM_TEST_MODE (no API key)"
PROMPT = "~/open-swarm$ "

# timing (ms)
TYPE_MS = 30          # per typing frame (~2 chars/frame)
TYPE_CHARS_PER_FRAME = 2
ENTER_PAUSE_MS = 400  # after a command is fully typed
OUTPUT_MS = 100       # per output-reveal frame (a few lines at a time)
OUTPUT_LINES_PER_FRAME = 3
SCENE_HOLD_MS = 2000  # hold at end of each scene
FINAL_HOLD_MS = 2500  # hold on the last scene before looping
MAX_TYPE_FRAMES = 40  # cap typing frames for very long commands


def load_font() -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, FONT_SIZE)
    sys.exit("DejaVu Sans Mono not found; install fonts-dejavu or edit FONT_CANDIDATES.")


def wrap(text: str, cols: int) -> list[str]:
    """Hard-wrap a line at terminal width, like a real terminal does."""
    if not text:
        return [""]
    return [text[i : i + cols] for i in range(0, len(text), cols)]


class Terminal:
    """Accumulates display lines and renders window-styled frames."""

    def __init__(self, font: ImageFont.FreeTypeFont):
        self.font = font
        self.char_w = font.getlength(" ")
        self.cols = int((WIDTH - 2 * PAD_X) / self.char_w)
        self.height = TITLEBAR_H + 2 * PAD_Y + ROWS * LINE_H
        self.lines: list[tuple[str, tuple[int, int, int]]] = []
        self.frames: list[Image.Image] = []
        self.durations: list[int] = []

    def _base(self) -> Image.Image:
        img = Image.new("RGB", (WIDTH, self.height), BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, WIDTH, TITLEBAR_H], fill=TITLEBAR_BG)
        for i, color in enumerate(TRAFFIC):
            cx = 18 + i * 22
            d.ellipse([cx - 6, TITLEBAR_H // 2 - 6, cx + 6, TITLEBAR_H // 2 + 6], fill=color)
        d.text((WIDTH // 2 - d.textlength(TITLE, font=self.font) // 2, TITLEBAR_H // 2 - FONT_SIZE // 2 - 1),
               TITLE, font=self.font, fill=FG_TITLE)
        return img

    def snapshot(self, duration_ms: int, partial: str | None = None, cursor: bool = False) -> None:
        """Render current lines (+ optional in-progress typed line) as a frame."""
        img = self._base()
        d = ImageDraw.Draw(img)
        rows: list[tuple[str, tuple[int, int, int]]] = list(self.lines)
        if partial is not None:
            color = FG_COMMENT if partial.startswith("#") else FG_COMMAND
            txt = PROMPT + partial + ("█" if cursor else "")
            for chunk in wrap(txt, self.cols):
                rows.append((chunk, color))
        visible = rows[-ROWS:]
        y = TITLEBAR_H + PAD_Y
        for text, color in visible:
            if text.startswith(PROMPT):
                d.text((PAD_X, y), PROMPT, font=self.font, fill=FG_PROMPT)
                d.text((PAD_X + self.char_w * len(PROMPT), y), text[len(PROMPT):], font=self.font, fill=color)
            else:
                d.text((PAD_X, y), text, font=self.font, fill=color)
            y += LINE_H
        self.frames.append(img)
        self.durations.append(duration_ms)

    def commit_command(self, cmd: str) -> None:
        color = FG_COMMENT if cmd.startswith("#") else FG_COMMAND
        for chunk in wrap(PROMPT + cmd, self.cols):
            self.lines.append((chunk, color))

    def type_command(self, cmd: str) -> None:
        step = TYPE_CHARS_PER_FRAME
        if len(cmd) / step > MAX_TYPE_FRAMES:
            step = max(step, round(len(cmd) / MAX_TYPE_FRAMES))
        for i in range(step, len(cmd) + 1, step):
            self.snapshot(TYPE_MS, partial=cmd[:i], cursor=True)
        self.snapshot(ENTER_PAUSE_MS, partial=cmd, cursor=False)
        self.commit_command(cmd)

    def print_output(self, block: list[str]) -> None:
        display: list[str] = []
        for line in block:
            display.extend(wrap(line, self.cols))
        for i in range(0, len(display), OUTPUT_LINES_PER_FRAME):
            for line in display[i : i + OUTPUT_LINES_PER_FRAME]:
                self.lines.append((line, FG_OUTPUT))
            self.snapshot(OUTPUT_MS)

    def clear(self) -> None:
        self.lines = []


def play_scene(term: Terminal, scene_path: Path) -> None:
    pending: list[str] = []
    for raw in scene_path.read_text().splitlines():
        if raw.startswith("$ "):
            if pending:
                term.print_output(pending)
                pending = []
            term.type_command(raw[2:])
        else:
            pending.append(raw)
    if pending:
        term.print_output(pending)


def main() -> None:
    font = load_font()
    term = Terminal(font)
    scenes = sorted(CAPTURES.glob("scene*.txt"))
    if not scenes:
        sys.exit(f"No scene files found in {CAPTURES}")
    for idx, scene in enumerate(scenes):
        if idx:
            term.clear()
        play_scene(term, scene)
        is_last = idx == len(scenes) - 1
        term.snapshot(FINAL_HOLD_MS if is_last else SCENE_HOLD_MS)

    # quantize against a shared palette so the GIF doesn't flicker
    palette_src = term.frames[-1].quantize(colors=64)
    pframes = [f.quantize(colors=64, palette=palette_src, dither=Image.Dither.NONE) for f in term.frames]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pframes[0].save(
        OUT_PATH,
        save_all=True,
        append_images=pframes[1:],
        duration=term.durations,
        loop=0,
        optimize=True,
    )
    total_s = sum(term.durations) / 1000
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"wrote {OUT_PATH} — {len(pframes)} frames, {total_s:.1f}s loop, {size_kb:.0f} KiB")


if __name__ == "__main__":
    main()
