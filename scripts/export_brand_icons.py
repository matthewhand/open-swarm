#!/usr/bin/env python3
"""Rasterise assets/brand SVG masters into checked-in PNG/ICO (+ SPA public copies).

Surfaces (#768 / #537 tasters):
  favicon-minimal.svg     → tab / PWA / small chrome rasters
  webui-geometric.svg     → in-app navbar / splash / settings copies
  marketing-cyber-swarm   → marketing PNG companion (from SVG + taster JPG)

Optional one-off tools (not runtime deps): Pillow + cairosvg.

    uv run --with pillow --with cairosvg python scripts/export_brand_icons.py
"""

from __future__ import annotations

import io
import shutil
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BRAND = REPO / "assets" / "brand"
PUBLIC = REPO / "webui" / "frontend" / "public"
HERO_FAVICON = REPO / "assets" / "images" / "favicon.ico"
TASTER_CYBER = BRAND / "tasters" / "option2-cyber-swarm-bee.jpg"

MINIMAL_SVG = BRAND / "favicon-minimal.svg"
MINIMAL_MONO_SVG = BRAND / "favicon-minimal-mono.svg"
MINIMAL_DARK_SVG = BRAND / "favicon-minimal-mono-on-dark.svg"
GEOMETRIC_SVG = BRAND / "webui-geometric.svg"
CYBER_SVG = BRAND / "marketing-cyber-swarm.svg"

FAVICON_SIZES = (16, 32, 48)
APP_COLOUR = (120, 152, 180, 192, 512)
MONO_SIZES = (16, 32, 192, 512)
MONO_DARK_SIZES = (16, 32, 192, 512)
GEOMETRIC_SIZES = (32, 64, 128, 256)
CYBER_SIZES = (256, 512, 1024)

SPA_COPIES = (
    "favicon.ico",
    "favicon-16.png",
    "favicon-32.png",
    "apple-touch-icon.png",
    "icon-192.png",
    "icon-512.png",
    "manifest.json",
    "webui-geometric.svg",
    "favicon-minimal.svg",
)


def _require_tools():
    try:
        import cairosvg  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        print(
            "Need Pillow + cairosvg (export-only, not a runtime dep):\n"
            "  uv run --with pillow --with cairosvg python scripts/export_brand_icons.py",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


def svg_png(svg: Path, size: int) -> "Image.Image":
    import cairosvg
    from PIL import Image

    raw = cairosvg.svg2png(url=str(svg), output_width=size, output_height=size)
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def save_png(image: "Image.Image", path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def write_ico(pngs: list["Image.Image"], path: Path) -> None:
    """Write a multi-size ICO with embedded PNGs (16/32/48).

    Pillow's ``save(..., format='ICO', append_images=...)`` often keeps only
    the first size; pack the directory ourselves.
    """
    blobs: list[tuple[int, int, bytes]] = []
    for im in pngs:
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        w, h = im.size
        blobs.append((w, h, buf.getvalue()))

    count = len(blobs)
    offset = 6 + 16 * count
    header = struct.pack("<HHH", 0, 1, count)
    entries = b""
    payload = b""
    for w, h, blob in blobs:
        entries += struct.pack(
            "<BBBBHHII",
            w if w < 256 else 0,
            h if h < 256 else 0,
            0,
            0,
            1,
            32,
            len(blob),
            offset,
        )
        payload += blob
        offset += len(blob)
    path.write_bytes(header + entries + payload)


def _export_taster_png() -> None:
    """Keep a lossless marketing PNG next to the SVG (fanfare photoreal)."""
    from PIL import Image

    if not TASTER_CYBER.is_file():
        return
    src = Image.open(TASTER_CYBER).convert("RGBA")
    src.save(BRAND / "marketing-cyber-swarm.png", format="PNG", optimize=True)


def main() -> int:
    _require_tools()
    if not MINIMAL_SVG.is_file():
        print(f"missing {MINIMAL_SVG}", file=sys.stderr)
        return 1
    if not GEOMETRIC_SVG.is_file():
        print(f"missing {GEOMETRIC_SVG}", file=sys.stderr)
        return 1

    colour = {s: svg_png(MINIMAL_SVG, s) for s in sorted(set(FAVICON_SIZES + APP_COLOUR))}
    mono = {s: svg_png(MINIMAL_MONO_SVG, s) for s in MONO_SIZES}
    mono_dark = {s: svg_png(MINIMAL_DARK_SVG, s) for s in MONO_DARK_SIZES}
    geometric = {s: svg_png(GEOMETRIC_SVG, s) for s in GEOMETRIC_SIZES}
    cyber = {s: svg_png(CYBER_SVG, s) for s in CYBER_SIZES if CYBER_SVG.is_file()}

    save_png(colour[16], BRAND / "favicon-16.png")
    save_png(colour[32], BRAND / "favicon-32.png")
    save_png(colour[48], BRAND / "favicon-48.png")
    write_ico([colour[16], colour[32], colour[48]], BRAND / "favicon.ico")

    # Masters already include the rounded-square field; do not re-pad.
    save_png(colour[120], BRAND / "apple-touch-icon-120.png")
    save_png(colour[152], BRAND / "apple-touch-icon-152.png")
    save_png(colour[180], BRAND / "apple-touch-icon.png")
    save_png(colour[192], BRAND / "icon-192.png")
    save_png(colour[512], BRAND / "icon-512.png")

    for size in MONO_SIZES:
        save_png(mono[size], BRAND / f"favicon-minimal-mono-{size}.png")

    for size in MONO_DARK_SIZES:
        save_png(mono_dark[size], BRAND / f"favicon-minimal-mono-on-dark-{size}.png")

    for size in GEOMETRIC_SIZES:
        save_png(geometric[size], BRAND / f"webui-geometric-{size}.png")

    for size, im in cyber.items():
        save_png(im, BRAND / f"marketing-cyber-swarm-{size}.png")
    if 512 in cyber:
        save_png(cyber[512], BRAND / "marketing-cyber-swarm.png")
    else:
        _export_taster_png()

    # Retired path: keep a copy so anything still pointing at the hero tree works.
    shutil.copy2(BRAND / "favicon.ico", HERO_FAVICON)

    PUBLIC.mkdir(parents=True, exist_ok=True)
    for name in SPA_COPIES:
        src = BRAND / name
        if src.is_file():
            shutil.copy2(src, PUBLIC / name)

    print(f"Wrote rasters under {BRAND} and SPA copies under {PUBLIC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
