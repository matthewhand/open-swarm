"""Unit tests for moa_orchestrator blueprint."""

from __future__ import annotations

from pathlib import Path

import pytest

from swarm.blueprints.moa_orchestrator.blueprint_moa_orchestrator import (
    MoAOrchestratorBlueprint,
)


@pytest.mark.asyncio
async def test_moa_orchestrator_blueprint_multi_task(tmp_path: Path):
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
    bp.set_params(
        {
            "workdir": str(tmp_path),
            "backend": "fake",
            "tasks": "implementer:apply decision|tester:verify|docs:write adr",
            "fake_responses": {
                "analyst": '{"claim":"ship it carefully","confidence":0.9}',
                "critic": '{"claim":"ship it carefully with tests","confidence":0.85}',
            },
            "participants": ["analyst", "critic"],
        }
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
    assert (tmp_path / "decision.md").is_file() or (tmp_path / "moa_determination.md").is_file()
