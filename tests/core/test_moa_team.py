"""Pure MoA team runner: consensus only vs consensus-then-team (no openai-agents)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from swarm.core.moa.team import (
    TeamTask,
    format_team_text,
    parse_team_tasks,
    run_moa_consensus,
    run_moa_then_team,
    team_result_to_payload,
)


@pytest.mark.asyncio
async def test_run_moa_consensus_only_no_writes():
    result = await run_moa_consensus(
        "Should we rate-limit?",
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses={
            "analyst": '{"claim":"yes token bucket","confidence":0.9}',
            "critic": '{"claim":"yes with metrics","confidence":0.85}',
        },
    )
    assert result.mode == "consensus_only"
    assert "token bucket" in result.determination.lower() or "yes" in result.determination.lower()
    assert result.specialist_results == []
    assert result.writes == []
    assert result.panel_wrote is False
    # Payload still has panel opinions
    opinions = result.moa_payload.get("opinions") or []
    assert len(opinions) == 2
    assert all(o.get("permission_mode") == "approve-reads" for o in opinions)


@pytest.mark.asyncio
async def test_run_moa_then_team_multi_specialists(tmp_path: Path):
    ws = tmp_path / "team"
    result = await run_moa_then_team(
        ws,
        "Should we enable edge rate limiting?",
        specialist_tasks=[
            TeamTask("implementer", "Write the decision", "decision.md"),
            TeamTask("tester", "Draft verification", "test_notes.md"),
            TeamTask("docs", "Write ADR", "docs/ADR.md"),
        ],
        seed_files={"notes.txt": "Public API; abuse risk high."},
        moa_backend="fake",
        moa_participants=["analyst", "critic"],
        moa_fake_responses={
            "analyst": '{"claim":"yes token bucket","confidence":0.9}',
            "critic": '{"claim":"yes token bucket with metrics","confidence":0.85}',
        },
    )
    assert result.mode == "consensus_then_team"
    assert "token bucket" in result.determination.lower()
    assert {s.persona for s in result.specialist_results} == {
        "implementer",
        "tester",
        "docs",
    }
    assert all(s.ok for s in result.specialist_results)
    assert (ws / "moa_determination.md").is_file()
    assert (ws / "decision.md").is_file()
    assert (ws / "test_notes.md").is_file()
    assert (ws / "docs" / "ADR.md").is_file()
    assert "decision.md" in result.writes
    # Footer documents pure path (not openai-agents)
    body = (ws / "decision.md").read_text(encoding="utf-8")
    assert "openai-agents" not in body.lower() or "no openai-agents" in body.lower()
    assert result.panel_wrote is False


@pytest.mark.asyncio
async def test_consensus_vs_team_contrast(tmp_path: Path):
    """Same question: consensus-only has no files; team path materializes artifacts."""
    q = "Ship rate limiting?"
    fakes = {
        "analyst": '{"claim":"ship carefully","confidence":0.9}',
        "critic": '{"claim":"ship carefully with tests","confidence":0.85}',
    }
    only = await run_moa_consensus(
        q, moa_backend="fake", moa_fake_responses=fakes
    )
    team = await run_moa_then_team(
        tmp_path / "ws",
        q,
        specialist_tasks=[
            TeamTask("implementer", "apply", "decision.md"),
            TeamTask("tester", "verify", "test_notes.md"),
        ],
        moa_backend="fake",
        moa_fake_responses=fakes,
    )
    assert only.mode == "consensus_only" and only.writes == []
    assert team.mode == "consensus_then_team"
    assert "decision.md" in team.writes
    assert "test_notes.md" in team.writes
    # Both share a non-empty determination from the same fake panel
    assert only.determination
    assert team.determination


def test_parse_team_tasks_string_and_at_path():
    tasks = parse_team_tasks(
        "implementer:Apply|tester:Verify@qa/notes.md|docs|researcher:scan"
    )
    assert tasks is not None
    by = {t.purpose: t for t in tasks}
    assert by["implementer"].output_path == "decision.md"
    assert by["tester"].output_path == "qa/notes.md"
    assert by["docs"].output_path == "docs/ADR.md"
    assert by["researcher"].instruction == "scan"
    assert parse_team_tasks("") is None
    assert parse_team_tasks(None) is None


@pytest.mark.asyncio
async def test_researcher_specialist_and_payload(tmp_path: Path):
    result = await run_moa_then_team(
        tmp_path / "r",
        "Map risks?",
        specialist_tasks=parse_team_tasks("researcher:Inventory|implementer:Decide"),
        seed_files={"notes.txt": "edge API"},
        moa_backend="fake",
        moa_fake_responses={
            "analyst": '{"claim":"inventory first","confidence":0.9}',
            "critic": '{"claim":"inventory then decide","confidence":0.85}',
        },
    )
    assert {s.persona for s in result.specialist_results} == {"researcher", "implementer"}
    assert (tmp_path / "r" / "research_notes.md").is_file()
    payload = team_result_to_payload(result, question="Map risks?")
    assert payload["mode"] == "consensus_then_team"
    assert payload["panel_wrote"] is False
    text = format_team_text(payload)
    assert "researcher" in text and "Writes" in text


@pytest.mark.asyncio
async def test_team_emits_info_logs(tmp_path: Path):
    """Attach a memory handler so we assert champagne INFO messages reliably."""
    records: list[str] = []

    class _ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record.getMessage())

    handler = _ListHandler(level=logging.INFO)
    loggers = [
        logging.getLogger("swarm.core.moa.team"),
        logging.getLogger("swarm.core.moa.orchestrator"),
    ]
    for log in loggers:
        log.addHandler(handler)
        log.setLevel(logging.INFO)
    try:
        await run_moa_consensus(
            "log check",
            moa_backend="fake",
            moa_fake_responses={
                "analyst": '{"claim":"a","confidence":0.9}',
                "critic": '{"claim":"b","confidence":0.8}',
            },
        )
        msgs = " ".join(records)
        assert "moa.team consensus_only start" in msgs
        assert "moa.collect" in msgs or "moa.run start" in msgs
        assert "moa.determine" in msgs

        records.clear()
        await run_moa_then_team(
            tmp_path / "logws",
            "log team",
            specialist_tasks=[TeamTask("implementer", "go", "decision.md")],
            moa_backend="fake",
            moa_fake_responses={
                "analyst": '{"claim":"yes","confidence":0.9}',
                "critic": '{"claim":"yes","confidence":0.8}',
            },
        )
        msgs = " ".join(records)
        assert "consensus_then_team start" in msgs
        assert "specialist start purpose=implementer" in msgs
        assert "panel_writes=[]" in msgs or "after_panel" in msgs
    finally:
        for log in loggers:
            log.removeHandler(handler)
