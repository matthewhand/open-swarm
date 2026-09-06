"""REQ-79 (#424) Survival: CLI/API chat works; prove open-swarm can update itself.

Locks contracts for:
1. Documentation and requirements tracking for REQ-79 / #424.
2. Honest session status lines for CLI and API turns (no fake restore on empty/new).
3. CLI session ID sanitization preventing argument injection or secret persistence.
4. Classification of restore kinds for CLI and API agents.
"""

from pathlib import Path

from swarm.core.cli_sessions import (
    sanitize_cli_session_id,
    session_notice_text,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REQ_DOC = REPO_ROOT / "docs" / "requirements" / "REQ-79.md"
FEATURE_STATUS = REPO_ROOT / "FEATURE_STATUS.md"
SESSION_RESTORE = REPO_ROOT / "webui" / "frontend" / "src" / "lib" / "sessionRestore.ts"


def test_req79_doc_and_feature_status():
    assert REQ_DOC.is_file(), "docs/requirements/REQ-79.md must exist"
    doc_text = REQ_DOC.read_text(encoding="utf-8")
    assert "https://github.com/matthewhand/open-swarm/issues/424" in doc_text
    assert "REQ-79" in doc_text
    assert "Self-update prove" in doc_text

    fs_text = FEATURE_STATUS.read_text(encoding="utf-8")
    assert "REQ-79 / #424" in fs_text
    assert "Survival CLI/API chat" in fs_text


def test_cli_session_sanitization_robustness():
    # Valid session tokens
    assert sanitize_cli_session_id("sess-1234-abcd") == "sess-1234-abcd"
    assert sanitize_cli_session_id("abc_def_99") == "abc_def_99"

    # Must reject non-strings or composite structures
    assert sanitize_cli_session_id(None) is None
    assert sanitize_cli_session_id(True) is None
    assert sanitize_cli_session_id(False) is None
    assert sanitize_cli_session_id(["session-id"]) is None
    assert sanitize_cli_session_id({"id": "123"}) is None

    # Must reject dangerous flags and path traversal
    assert sanitize_cli_session_id("--flag") is None
    assert sanitize_cli_session_id("-rf") is None
    assert sanitize_cli_session_id("../escape") is None
    assert sanitize_cli_session_id("a/b") is None
    assert sanitize_cli_session_id("a\\b") is None
    assert sanitize_cli_session_id("id with spaces") is None

    # Must reject secret tokens
    assert sanitize_cli_session_id("sk-proj-1234567890abcdef") is None
    assert sanitize_cli_session_id("ghp_1234567890abcdef") is None


def test_honest_session_notices():
    # Resumed notice
    resumed_line = session_notice_text("claude", resumed=True)
    assert resumed_line == "Resumed claude session."
    assert "new" not in resumed_line.lower()

    # New session notice
    new_line = session_notice_text("claude", resumed=False)
    assert new_line == "Started a new claude session."
    assert "resumed" not in new_line.lower()


def test_session_restore_frontend_contract():
    assert SESSION_RESTORE.is_file()
    src = SESSION_RESTORE.read_text(encoding="utf-8")
    assert "cli: 'Resumed CLI session'" in src
    assert "api: 'Restored session'" in src
    assert "hasRestorableTurns" in src
