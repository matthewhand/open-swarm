"""Static checks for GitHub marketplace tab JS in blueprint_library.js."""

from pathlib import Path

JS = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "swarm"
    / "static"
    / "js"
    / "blueprint_library.js"
)


def _js() -> str:
    return JS.read_text(encoding="utf-8")


def test_marketplace_rejects_non_ok_http_status():
    js = _js()
    assert "if (!resp.ok)" in js
    assert "Could not load marketplace results." in js


def test_marketplace_repo_links_allow_only_http_https():
    js = _js()
    assert "function safeHttpUrl" in js
    assert "u.protocol === 'http:'" in js
    assert "u.protocol === 'https:'" in js
    assert "javascript:" not in js.lower() or "does not stop javascript:" in js.lower()
