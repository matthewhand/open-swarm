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
    # Legitimate write still works
    tools.write_file("ok.txt", "safe")
    assert (root / "ok.txt").read_text(encoding="utf-8") == "safe"


def test_workspace_tools_rejects_absolute_escape(tmp_path: Path):
    tools = WorkspaceTools(tmp_path / "ws")
    with pytest.raises(ValueError, match="escapes workspace"):
        tools.read_file("/etc/passwd")


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
