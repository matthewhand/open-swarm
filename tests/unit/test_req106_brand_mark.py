"""REQ-106: bee brand mark kit + SPA/Django favicon wiring."""

from __future__ import annotations

import json
import struct
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from django.test import Client

REPO = Path(__file__).resolve().parents[2]
BRAND = REPO / "assets" / "brand"
PUBLIC = REPO / "webui" / "frontend" / "public"
SPA_INDEX = REPO / "webui" / "frontend" / "index.html"
BASE = REPO / "src" / "swarm" / "templates" / "base.html"
LOGIN = REPO / "src" / "swarm" / "templates" / "account" / "login.html"
INCLUDE = REPO / "src" / "swarm" / "templates" / "includes" / "brand_icons.html"
PINOKIO = REPO / "pinokio.js"
HERO_JPG = REPO / "assets" / "images" / "openswarm-project-image.jpg"
OLD_ICO = REPO / "assets" / "images" / "favicon.ico"

COLOUR_SVG = BRAND / "bee-mark.svg"
MONO_SVG = BRAND / "bee-mark-mono.svg"
MONO_DARK_SVG = BRAND / "bee-mark-mono-on-dark.svg"

PNG_SIZES = {
    "favicon-16.png": 16,
    "favicon-32.png": 32,
    "favicon-48.png": 48,
    "apple-touch-icon.png": 180,
    "apple-touch-icon-120.png": 120,
    "apple-touch-icon-152.png": 152,
    "icon-192.png": 192,
    "icon-512.png": 512,
    "bee-mark-mono-16.png": 16,
    "bee-mark-mono-32.png": 32,
    "bee-mark-mono-192.png": 192,
    "bee-mark-mono-512.png": 512,
    "bee-mark-mono-on-dark-16.png": 16,
    "bee-mark-mono-on-dark-32.png": 32,
    "bee-mark-mono-on-dark-192.png": 192,
    "bee-mark-mono-on-dark-512.png": 512,
}

SPA_COPIES = (
    "favicon.ico",
    "favicon-16.png",
    "favicon-32.png",
    "apple-touch-icon.png",
    "icon-192.png",
    "icon-512.png",
    "manifest.json",
)

ROOT_ICON_URLS = (
    ("/favicon.ico", "image/x-icon", b"\x00\x00\x01\x00"),
    ("/favicon-16.png", "image/png", b"\x89PNG\r\n\x1a\n"),
    ("/favicon-32.png", "image/png", b"\x89PNG\r\n\x1a\n"),
    ("/apple-touch-icon.png", "image/png", b"\x89PNG\r\n\x1a\n"),
    ("/icon-192.png", "image/png", b"\x89PNG\r\n\x1a\n"),
    ("/icon-512.png", "image/png", b"\x89PNG\r\n\x1a\n"),
)


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return struct.unpack(">II", data[16:24])


def _ico_sizes(path: Path) -> list[tuple[int, int]]:
    data = path.read_bytes()
    assert data[:4] == b"\x00\x00\x01\x00"
    count = int.from_bytes(data[4:6], "little")
    sizes = []
    off = 6
    for _ in range(count):
        w = data[off] or 256
        h = data[off + 1] or 256
        sizes.append((w, h))
        off += 16
    return sizes


def test_hero_banner_jpg_is_not_replaced():
    assert HERO_JPG.is_file()
    assert HERO_JPG.stat().st_size > 50_000


def test_master_svgs_are_simple_original_bees():
    colour = COLOUR_SVG.read_text(encoding="utf-8")
    mono = MONO_SVG.read_text(encoding="utf-8")
    dark = MONO_DARK_SVG.read_text(encoding="utf-8")
    for text in (colour, mono, dark):
        assert "<svg" in text
        ET.fromstring(text)
        assert "clipPath" in text or "ellipse" in text
        assert "shutterstock" not in text.lower()
        assert "neon" not in text.lower()
        # Photo-real wing veins would be a mesh of tiny paths; we keep two lobes.
        assert text.count("<ellipse") >= 2
    assert "#F4C400" in colour
    assert "#1A140C" in colour
    assert "currentColor" in mono
    assert "#FFFFFF" in dark
    assert "#111111" in dark or "111111" in dark or "dark" in dark.lower()


def test_raster_checklist_and_png_dimensions():
    for name, size in PNG_SIZES.items():
        path = BRAND / name
        assert path.is_file(), name
        width, height = _png_size(path)
        assert (width, height) == (size, size), f"{name}: {width}x{height}"


def test_favicon_ico_is_16_32_48():
    ico = BRAND / "favicon.ico"
    assert ico.is_file()
    assert set(_ico_sizes(ico)) == {(16, 16), (32, 32), (48, 48)}
    assert OLD_ICO.read_bytes() == ico.read_bytes()


def test_spa_public_copies_match_brand():
    for name in SPA_COPIES:
        src = BRAND / name
        dest = PUBLIC / name
        assert src.is_file(), name
        assert dest.is_file(), name
        assert src.read_bytes() == dest.read_bytes(), name


def test_manifest_lists_pwa_colour_icons():
    manifest = json.loads((BRAND / "manifest.json").read_text(encoding="utf-8"))
    srcs = {icon["src"] for icon in manifest["icons"]}
    assert "/icon-192.png" in srcs
    assert "/icon-512.png" in srcs
    assert manifest["theme_color"] == "#111111"


def test_html_heads_reference_brand_icons():
    spa = SPA_INDEX.read_text(encoding="utf-8")
    include = INCLUDE.read_text(encoding="utf-8")
    base = BASE.read_text(encoding="utf-8")
    login = LOGIN.read_text(encoding="utf-8")
    assert 'rel="icon" href="/favicon.ico"' in spa
    assert 'href="/favicon-16.png"' in spa
    assert 'href="/favicon-32.png"' in spa
    assert 'rel="apple-touch-icon" href="/apple-touch-icon.png"' in spa
    assert 'rel="manifest" href="/manifest.json"' in spa
    assert "includes/brand_icons.html" in base
    assert "includes/brand_icons.html" in login
    assert "brand/favicon.ico" in include
    assert "brand/apple-touch-icon.png" in include
    assert "brand/manifest.json" in include


def test_pinokio_uses_colour_bee_svg():
    text = PINOKIO.read_text(encoding="utf-8")
    assert "assets/brand/bee-mark.svg" in text
    assert "rest_mode/svg/logo.svg" not in text


@pytest.mark.django_db
def test_root_icon_urls_are_not_html(client: Client):
    for url, ctype, magic in ROOT_ICON_URLS:
        response = client.get(url)
        assert response.status_code == 200, url
        assert ctype in response["Content-Type"], url
        assert response.content.startswith(magic), url
        assert b"<html" not in response.content[:200].lower()
        assert getattr(response, "streaming", False) is False

    manifest = client.get("/manifest.json")
    assert manifest.status_code == 200
    assert "manifest" in manifest["Content-Type"] or "json" in manifest["Content-Type"]
    body = json.loads(manifest.content)
    assert body["name"] == "Open Swarm"


@pytest.mark.django_db
def test_django_static_brand_icons_resolve(client: Client):
    response = client.get("/static/brand/favicon.ico")
    assert response.status_code == 200
    assert response.content == (BRAND / "favicon.ico").read_bytes()
    png = client.get("/static/brand/favicon-16.png")
    assert png.status_code == 200
    assert png.content.startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.django_db
def test_operator_and_login_html_link_static_brand(client: Client):
    login = client.get("/login/")
    assert login.status_code == 200
    html = login.content.decode("utf-8")
    assert "brand/favicon.ico" in html
    assert "brand/apple-touch-icon.png" in html
    assert "brand/manifest.json" in html
