"""Regression: medium XSS sinks must escape / gate untrusted values.

Covers rest_mode toast.js, blueprint_creator showSuccessModal, and
profiles.html base_url href (javascript: protocol).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOAST_JS = ROOT / "src" / "swarm" / "static" / "rest_mode" / "js" / "toast.js"
BLUEPRINT_CREATOR = ROOT / "src" / "swarm" / "templates" / "blueprint_creator.html"
PROFILES = ROOT / "src" / "swarm" / "templates" / "profiles.html"


def _slice_after(source: str, marker: str, length: int = 1200) -> str:
    idx = source.find(marker)
    assert idx != -1, f"marker not found: {marker}"
    return source[idx : idx + length]


def test_rest_mode_toast_escapes_message():
    source = TOAST_JS.read_text(encoding="utf-8")
    body = _slice_after(source, "export function showToast")
    assert "escapeHtml(message)" in body
    assert re.search(r"<span>\$\{\s*message\s*\}</span>", body) is None
    assert "function escapeHtml" in source


def test_blueprint_creator_show_success_modal_escapes_fields():
    source = BLUEPRINT_CREATOR.read_text(encoding="utf-8")
    body = _slice_after(source, "function showSuccessModal")
    assert "escapeHtml(blueprint.name)" in body
    assert "escapeHtml(blueprint.category)" in body
    assert "escapeHtml(blueprint.author)" in body
    assert "escapeHtml(blueprint.created_at)" in body
    assert "escapeHtml(blueprint.description)" in body
    assert "escapeHtml(tag)" in body
    assert re.search(r"\$\{\s*blueprint\.(name|category|author|created_at|description)\s*\}", body) is None
    assert re.search(r"\$\{\s*tag\s*\}", body) is None
    assert "function escapeHtml" in source


def test_profiles_base_url_href_gated_to_http_https():
    source = PROFILES.read_text(encoding="utf-8")
    # Must not use raw base_url as href without an http(s) gate.
    assert 'href="{{ p.base_url }}"' in source
    assert 'u|slice:":8" == "https://"' in source
    assert 'u|slice:":7" == "http://"' in source
    # Non-http(s) values render as text, not a link.
    assert '<span class="prof-url">{{ p.base_url }}</span>' in source
