"""Regression tests for skeptic-flagged bugs (path escape + vote-weight answer)."""

from __future__ import annotations

from pathlib import Path

import pytest

from swarm.core.moa import MoAOrchestrator
from swarm.core.moa.backends import FakeParticipantBackend
from swarm.core.persona_swarm import WorkspaceTools


def test_workspace_tools_rejects_sibling_path_escape(tmp_path: Path):
    """../ws_evil must not resolve under a different sibling of root."""
    root = tmp_path / "ws_good"
    evil = tmp_path / "ws_evil"
    root.mkdir()
    evil.mkdir()
    tools = WorkspaceTools(root)

    with pytest.raises(ValueError, match="escapes workspace"):
        tools.write_file("../ws_evil/pwned.txt", "nope")

    assert not (evil / "pwned.txt").exists()
    # Failed escapes must not pollute the write audit trail
    assert "../ws_evil/pwned.txt" not in tools.writes
    # Legitimate write still works
    tools.write_file("ok.txt", "safe")
    assert (root / "ok.txt").read_text(encoding="utf-8") == "safe"
    assert tools.writes == ["ok.txt"]


def test_workspace_tools_rejects_absolute_escape(tmp_path: Path):
    tools = WorkspaceTools(tmp_path / "ws")
    with pytest.raises(ValueError, match="escapes workspace"):
        tools.read_file("/etc/passwd")
    assert tools.reads == []
    with pytest.raises(ValueError, match="escapes workspace"):
        tools.write_file("/etc/passwd", "nope")
    assert tools.writes == []
    with pytest.raises(ValueError, match="escapes workspace"):
        tools.list_files("../")
    assert tools.reads == []


def test_workspace_tools_rejects_dotdot_etc_passwd(tmp_path: Path):
    """Classic ../../etc/passwd style climb from workspace root."""
    tools = WorkspaceTools(tmp_path / "ws")
    with pytest.raises(ValueError, match="escapes workspace"):
        tools.write_file("../../etc/passwd", "pwned")
    assert tools.writes == []
    # Nested relative that stays inside root is allowed; trace is normalized.
    tools.write_file("subdir/../ok.md", "safe")
    assert (tmp_path / "ws" / "ok.md").read_text(encoding="utf-8") == "safe"
    assert tools.writes == ["ok.md"]


def test_workspace_tools_portable_backslash_paths(tmp_path: Path):
    """Backslash separators must nest (not literal names) and still block escapes.

    On POSIX, bare ``Path(root) / r'docs\\x'`` treats ``\\`` as a filename char;
    WorkspaceTools normalizes so Windows-style relative paths work everywhere.
    """
    root = tmp_path / "ws_good"
    evil = tmp_path / "ws_evil"
    root.mkdir()
    evil.mkdir()
    tools = WorkspaceTools(root)

    tools.write_file(r"docs\ADR.md", "# adr\n")
    assert (root / "docs" / "ADR.md").read_text(encoding="utf-8") == "# adr\n"
    assert tools.writes == ["docs/ADR.md"]

    tools.write_file(Path("nested") / "via_path.txt", "ok")
    assert (root / "nested" / "via_path.txt").is_file()
    assert "nested/via_path.txt" in tools.writes

    with pytest.raises(ValueError, match="escapes workspace"):
        tools.write_file(r"..\ws_evil\pwned.txt", "nope")
    assert not (evil / "pwned.txt").exists()
    assert tools.writes == ["docs/ADR.md", "nested/via_path.txt"]


def test_workspace_tools_rejects_windows_absolute_and_unc(tmp_path: Path):
    """Drive letters, drive-relative, and UNC paths must not join under root."""
    tools = WorkspaceTools(tmp_path / "ws")
    for bad in (
        r"C:\Windows\System32\drivers\etc\hosts",
        "C:/Windows/System32/drivers/etc/hosts",
        "C:foo",
        r"\\server\share\secret",
        "//server/share/secret",
        r"\absolute\from\drive",
    ):
        with pytest.raises(ValueError, match="escapes workspace"):
            tools.read_file(bad)
    assert tools.reads == []


@pytest.mark.asyncio
async def test_vote_weights_align_answer_with_weighted_primary():
    """Heavy weight on B must make answer start with B's claim, not A."""
    backend = FakeParticipantBackend(
        {
            "a": '{"claim":"option A", "confidence":0.9}',
            "b": '{"claim":"option B", "confidence":0.5}',
        }
    )
    orch = MoAOrchestrator(
        backend=backend,
        vote_weights={"a": 0.1, "b": 10.0},
    )
    result = await orch.run("pick", ["a", "b"])
    assert result.determination is not None
    det = result.determination
    assert det.analysis is not None
    assert det.analysis.get("primary") == "b"
    # Answer must lead with the weighted primary's claim
    assert det.answer.strip().lower().startswith("option b")
    assert "option a" not in det.answer.split("\n")[0].lower()
    assert "vote-weighted" in det.answer.lower() or "vote-weighted" in det.rationale.lower()
