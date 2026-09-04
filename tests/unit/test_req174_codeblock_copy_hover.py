from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_CSS = REPO_ROOT / "webui" / "frontend" / "src" / "index.css"
CODE_FENCES_TS = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "codeFences.ts"


def test_code_copy_concealed_by_default_in_css():
    """index.css must conceal .os-code-copy with opacity: 0 at rest."""
    css = INDEX_CSS.read_text(encoding="utf-8")
    assert ".os-code-copy {" in css
    assert "opacity: 0;" in css


def test_code_copy_revealed_on_hover_and_focus_within():
    """index.css must reveal .os-code-copy on codeblock hover and focus-within."""
    css = INDEX_CSS.read_text(encoding="utf-8")
    assert ".os-code:hover .os-code-copy" in css or "pre:hover .os-code-copy" in css
    assert "focus-within .os-code-copy" in css


def test_code_copy_always_visible_on_touch_mobile():
    """index.css must keep .os-code-copy visible on touch devices without hover."""
    css = INDEX_CSS.read_text(encoding="utf-8")
    assert "@media (hover: none)" in css


def test_code_fences_adds_os_code_class():
    """codeFences.ts must add os-code class to pre elements for relative positioning and hover."""
    ts = CODE_FENCES_TS.read_text(encoding="utf-8")
    assert "pre.classList.add('os-code')" in ts
    assert "code-copy" in ts
