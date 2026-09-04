"""Lock ADR-005 look-only computer-control proposal (REQ-189 / #645).

Docs only. No driver, sandbox, or chrome change in the ADR PR.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADR = REPO / "docs" / "adr" / "005-local-computer-control.md"
ADR_INDEX = REPO / "docs" / "adr" / "README.md"
REQ = REPO / "docs" / "requirements" / "REQ-189.md"


def test_adr005_exists_and_is_look_only():
    text = ADR.read_text(encoding="utf-8")
    assert "REQ-189" in text
    assert "#645" in text
    assert "SaaS" in text and "deferred" in text.lower()
    assert "SandboxProvider" in text
    assert "cua-driver" in text
    assert "Does not close #645" in text or "does **not** close #645" in text.lower()
    assert "Fixes #645" not in text
    assert "No runtime" in text or "no runtime change" in text.lower()


def test_adr005_is_indexed_and_req_pointer_exists():
    index = ADR_INDEX.read_text(encoding="utf-8")
    assert "005-local-computer-control.md" in index
    assert "REQ-189" in index
    req = REQ.read_text(encoding="utf-8")
    assert "https://github.com/matthewhand/open-swarm/issues/645" in req
    assert "005-local-computer-control.md" in req
