"""Unit tests for moa_orchestrator blueprint (post team-refactor)."""

from __future__ import annotations

from pathlib import Path

import pytest

from swarm.blueprints.moa_orchestrator.blueprint_moa_orchestrator import (
    MoAOrchestratorBlueprint,
)
from swarm.core.moa.team import TeamTask, parse_team_tasks

WS = "orch-run"


def _bp(tmp_path: Path, monkeypatch, **params) -> tuple[MoAOrchestratorBlueprint, Path]:
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(tmp_path))
    monkeypatch.delenv("ALLOW_UNRESTRICTED_WORKDIR", raising=False)
    bp = MoAOrchestratorBlueprint(blueprint_id="moa_orchestrator")
    bp._config = {
        "moa": {
            "backend": "fake",
            "participants": ["analyst", "critic"],
            "fake_responses": {
                "analyst": '{"claim":"ship it carefully","confidence":0.9}',
                "critic": '{"claim":"ship it carefully with tests","confidence":0.85}',
            },
        }
    }
    base = {
        "workdir": WS,
        "backend": "fake",
        "fake_responses": {
            "analyst": '{"claim":"ship it carefully","confidence":0.9}',
            "critic": '{"claim":"ship it carefully with tests","confidence":0.85}',
        },
        "participants": ["analyst", "critic"],
    }
    base.update(params)
    bp.set_params(base)
    return bp, tmp_path / WS


@pytest.mark.asyncio
async def test_moa_orchestrator_blueprint_multi_task(tmp_path: Path, monkeypatch):
    bp, ws = _bp(
        tmp_path,
        monkeypatch,
        tasks="implementer:apply decision|tester:verify|docs:write adr",
    )
    chunks = []
    async for c in bp.run([{"role": "user", "content": "Ship feature X?"}]):
        chunks.append(c)
    final = chunks[-1]
    assert final.get("final") is True
    assert final["meta"].get("moa_orchestrator") is True
    specialists = final["meta"].get("specialists") or []
    assert "implementer" in specialists
    assert "tester" in specialists
    assert (ws / "decision.md").is_file()
    assert (ws / "test_notes.md").is_file()
    assert (ws / "docs" / "ADR.md").is_file()
    assert (ws / "moa_determination.md").is_file()


@pytest.mark.asyncio
async def test_moa_orchestrator_at_path_custom_outputs(tmp_path: Path, monkeypatch):
    """params.tasks @path syntax routes specialist writes to custom paths."""
    bp, ws = _bp(
        tmp_path,
        monkeypatch,
        tasks=(
            "implementer:Apply decision@artifacts/decision.md"
            "|tester:Verify@qa/test_notes.md"
            "|docs:Write ADR@docs/custom_ADR.md"
        ),
    )
    chunks = []
    async for c in bp.run([{"role": "user", "content": "Ship rate limiting?"}]):
        chunks.append(c)
    final = chunks[-1]
    assert final.get("final") is True
    assert (ws / "artifacts" / "decision.md").is_file()
    assert (ws / "qa" / "test_notes.md").is_file()
    assert (ws / "docs" / "custom_ADR.md").is_file()
    writes = final["meta"].get("writes") or []
    assert any("decision.md" in w for w in writes)
    assert any("test_notes.md" in w for w in writes)
    # Default paths must NOT be used when @path is given
    assert not (ws / "decision.md").exists()
    assert not (ws / "test_notes.md").exists()


@pytest.mark.asyncio
async def test_moa_orchestrator_tasks_list_of_dicts(tmp_path: Path, monkeypatch):
    """API-style list-of-dicts tasks with explicit output_path."""
    bp, ws = _bp(
        tmp_path,
        monkeypatch,
        tasks=[
            {
                "purpose": "implementer",
                "instruction": "Apply",
                "output_path": "out/impl.md",
            },
            {"purpose": "researcher", "instruction": "Inventory workspace"},
        ],
    )
    chunks = []
    async for c in bp.run([{"role": "user", "content": "Map and decide?"}]):
        chunks.append(c)
    final = chunks[-1]
    assert "implementer" in (final["meta"].get("specialists") or [])
    assert "researcher" in (final["meta"].get("specialists") or [])
    assert (ws / "out" / "impl.md").is_file()
    assert (ws / "research_notes.md").is_file()  # researcher default


@pytest.mark.asyncio
async def test_moa_orchestrator_team_tasks_alias(tmp_path: Path, monkeypatch):
    """CLI-style team_tasks alias works when tasks is unset."""
    bp, ws = _bp(tmp_path, monkeypatch, team_tasks="implementer:go@out.md")
    # ensure tasks key is absent
    bp._params.pop("tasks", None)
    chunks = []
    async for c in bp.run([{"role": "user", "content": "Go?"}]):
        chunks.append(c)
    assert chunks[-1].get("final") is True
    assert (ws / "out.md").is_file()


@pytest.mark.asyncio
async def test_moa_orchestrator_default_implementer_when_no_tasks(tmp_path: Path, monkeypatch):
    bp, ws = _bp(tmp_path, monkeypatch)
    bp._params.pop("tasks", None)
    bp._params.pop("team_tasks", None)
    chunks = []
    async for c in bp.run([{"role": "user", "content": "Decide?"}]):
        chunks.append(c)
    final = chunks[-1]
    assert final["meta"].get("specialists") == ["implementer"]
    assert (ws / "decision.md").is_file()


@pytest.mark.asyncio
async def test_moa_orchestrator_empty_prompt():
    bp = MoAOrchestratorBlueprint(blueprint_id="moa_orchestrator")
    bp.set_params({})
    chunks = []
    async for c in bp.run([]):
        chunks.append(c)
    assert len(chunks) == 1
    assert chunks[0]["final"] is True
    assert "No prompt" in chunks[0]["content"]


@pytest.mark.asyncio
async def test_moa_orchestrator_participants_csv_string(tmp_path: Path, monkeypatch):
    bp, _ws = _bp(tmp_path, monkeypatch, participants="analyst, critic", tasks="implementer:x")
    chunks = []
    async for c in bp.run([{"role": "user", "content": "Q?"}]):
        chunks.append(c)
    assert chunks[-1]["meta"]["backends"] == ["analyst", "critic"]


@pytest.mark.asyncio
async def test_moa_orchestrator_test_mode_forces_fake_backend(tmp_path: Path, monkeypatch):
    """Under SWARM_TEST_MODE, config backend is clamped to fake unless params override."""
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(tmp_path))
    monkeypatch.delenv("ALLOW_UNRESTRICTED_WORKDIR", raising=False)
    bp = MoAOrchestratorBlueprint(blueprint_id="moa_orchestrator")
    bp._config = {"moa": {"backend": "grok", "participants": ["analyst", "critic"]}}
    bp.set_params(
        {
            "workdir": "test-mode-run",
            # no backend in params — config says grok, TEST_MODE forces fake
            "fake_responses": {
                "analyst": '{"claim":"ok","confidence":0.9}',
                "critic": '{"claim":"ok","confidence":0.85}',
            },
            "tasks": "implementer:apply",
        }
    )
    assert bp._moa_settings().get("backend") == "fake"
    chunks = []
    async for c in bp.run([{"role": "user", "content": "ping"}]):
        chunks.append(c)
    assert chunks[-1].get("final") is True
    ws = tmp_path / "test-mode-run"
    assert (ws / "decision.md").is_file() or (ws / "moa_determination.md").is_file()


def test_parse_tasks_delegate_matches_shared_parser():
    bp = MoAOrchestratorBlueprint(blueprint_id="moa_orchestrator")
    bp.set_params({"tasks": "tester:Verify@qa/notes.md|docs"})
    parsed = bp._parse_tasks()
    shared = parse_team_tasks("tester:Verify@qa/notes.md|docs")
    assert parsed is not None and shared is not None
    assert [(t.purpose, t.instruction, t.output_path) for t in parsed] == [
        (t.purpose, t.instruction, t.output_path) for t in shared
    ]
    assert parsed[0].output_path == "qa/notes.md"
    assert parsed[1].output_path == "docs/ADR.md"


def test_parse_tasks_accepts_team_task_instance():
    bp = MoAOrchestratorBlueprint(blueprint_id="moa_orchestrator")
    t = TeamTask("implementer", "go", "x.md")
    bp.set_params({"tasks": [t]})
    assert bp._parse_tasks() == [t]
