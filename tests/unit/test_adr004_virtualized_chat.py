"""REQ-163 / ADR-004: Phase 0 virtualized-chat decision stays honest."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADR = REPO / "docs" / "adr" / "004-virtualized-chat-history.md"
INDEX = REPO / "docs" / "adr" / "README.md"
FEATURE_STATUS = REPO / "FEATURE_STATUS.md"
PACKAGE = REPO / "webui" / "frontend" / "package.json"


def test_adr004_exists_and_picks_tanstack_virtual():
    text = ADR.read_text(encoding="utf-8")
    assert "ADR-004" in text
    assert "REQ-163" in text
    assert "#575" in text
    assert "Proposed" in text
    assert "@tanstack/react-virtual" in text
    assert "3.14" in text
    assert "anchorTo" in text
    assert "followOnAppend" in text
    assert "scrollToEnd" in text
    assert "react-virtuoso" in text
    assert "react-window" in text
    assert "@tanstack/react-query" in text
    assert "useInfiniteQuery" in text
    # Commercial Message List stays out of the FOSS chat path.
    assert "commercial" in text.lower()
    assert "@virtuoso.dev/message-list" in text
    # No committed secret material.
    assert "sk-" not in text


def test_adr004_is_indexed():
    index = INDEX.read_text(encoding="utf-8")
    assert "004-virtualized-chat-history.md" in index
    assert "@tanstack/react-virtual" in index


def test_feature_status_marks_virtualized_chat_planned():
    text = FEATURE_STATUS.read_text(encoding="utf-8")
    assert "REQ-163" in text
    assert "ADR-004" in text
    assert "📋" in text
    assert "@tanstack/react-virtual" in text


def test_spa_has_react_query_not_a_virtualizer_yet():
    """Look-only: Query is already the data layer; no virtualizer dep yet."""
    text = PACKAGE.read_text(encoding="utf-8")
    assert "@tanstack/react-query" in text
    assert "@tanstack/react-virtual" not in text
    assert "react-virtuoso" not in text
    assert "react-window" not in text
    assert "react-virtualized" not in text
