"""REQ-151 / ADR-003: Phase 0 desktop packaging decision stays honest."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADR = REPO / "docs" / "adr" / "003-desktop-packaging.md"
INDEX = REPO / "docs" / "adr" / "README.md"
FEATURE_STATUS = REPO / "FEATURE_STATUS.md"


def test_adr003_exists_and_picks_pywebview_not_electron():
    text = ADR.read_text(encoding="utf-8")
    assert "ADR-003" in text
    assert "REQ-151" in text
    assert "#554" in text
    assert "Proposed" in text
    assert "pywebview" in text
    assert "PyInstaller" in text
    assert "127.0.0.1" in text
    assert "WebView2" in text
    # Product shape matches OpenMausBot; toolkit does not.
    assert "Electron" in text
    assert "Do not copy Electron" in text or "not Electron" in text
    assert "No installer" in text or "no installer" in text
    # Native CLIs stay on the host (pane of glass).
    assert "grok" in text and "agy" in text
    assert "Neon" in text
    # No committed secret material.
    assert "sk-" not in text
    assert "token_urlsafe" in text  # first-run generation, not a literal key


def test_adr003_is_indexed():
    index = INDEX.read_text(encoding="utf-8")
    assert "003-desktop-packaging.md" in index
    assert "pywebview" in index


def test_feature_status_marks_desktop_planned():
    text = FEATURE_STATUS.read_text(encoding="utf-8")
    assert "REQ-151" in text
    assert "ADR-003" in text
    assert "📋" in text
    assert "pywebview" in text
