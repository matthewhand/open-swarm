#!/usr/bin/env python3
"""Rasterise assets/brand SVG masters into checked-in PNG/ICO (+ SPA public copies).

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

COLOUR_SVG = BRAND / "bee-mark.svg"
MONO_SVG = BRAND / "bee-mark-mono.svg"
MONO_DARK_SVG = BRAND / "bee-mark-mono-on-dark.svg"

# Cream field for opaque Apple / PWA colour icons (iOS paints transparent as black).
PWA_BG = (255, 248, 236, 255)  # #FFF8EC
DARK_BG = (17, 17, 17, 255)  # DaisyUI rail #111111

# Colour transparent favicons (tab).
FAVICON_SIZES = (16, 32, 48)
# Colour opaque app icons.
APP_COLOUR = (120, 152, 180, 192, 512)
# Mono transparent (masks / light UI).
MONO_SIZES = (16, 32, 192, 512)
# White-on-#111111 (dark chrome).
MONO_DARK_SIZES = (16, 32, 192, 512)

SPA_COPIES = (
    "favicon.ico",
    "favicon-16.png",
    "favicon-32.png",
    "apple-touch-icon.png",
    "icon-192.png",
    "icon-512.png",
    "manifest.json",
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


def on_field(bee: "Image.Image", rgba: tuple[int, int, int, int], pad_ratio: float = 0.10) -> "Image.Image":
    from PIL import Image

    size = bee.size[0]
    field = Image.new("RGBA", (size, size), rgba)
    inset = max(1, int(size * pad_ratio))
    inner = size - inset * 2
    scaled = bee.resize((inner, inner), Image.Resampling.LANCZOS)
    field.paste(scaled, (inset, inset), scaled)
    return field


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


def main() -> int:
    _require_tools()
    if not COLOUR_SVG.is_file():
        print(f"missing {COLOUR_SVG}", file=sys.stderr)
        return 1

    colour = {s: svg_png(COLOUR_SVG, s) for s in sorted(set(FAVICON_SIZES + APP_COLOUR))}
    mono = {s: svg_png(MONO_SVG, s) for s in MONO_SIZES}
    mono_dark_bee = {s: svg_png(MONO_DARK_SVG, s) for s in MONO_DARK_SIZES}

    save_png(colour[16], BRAND / "favicon-16.png")
    save_png(colour[32], BRAND / "favicon-32.png")
    save_png(colour[48], BRAND / "favicon-48.png")
    write_ico([colour[16], colour[32], colour[48]], BRAND / "favicon.ico")

    save_png(on_field(colour[120], PWA_BG), BRAND / "apple-touch-icon-120.png")
    save_png(on_field(colour[152], PWA_BG), BRAND / "apple-touch-icon-152.png")
    apple_180 = on_field(colour[180], PWA_BG)
    save_png(apple_180, BRAND / "apple-touch-icon.png")
    save_png(on_field(colour[192], PWA_BG), BRAND / "icon-192.png")
    save_png(on_field(colour[512], PWA_BG), BRAND / "icon-512.png")

    for size in MONO_SIZES:
        save_png(mono[size], BRAND / f"bee-mark-mono-{size}.png")

    for size in MONO_DARK_SIZES:
        save_png(on_field(mono_dark_bee[size], DARK_BG, pad_ratio=0.12), BRAND / f"bee-mark-mono-on-dark-{size}.png")

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
