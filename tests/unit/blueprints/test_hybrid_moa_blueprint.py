"""Unit tests for hybrid_moa blueprint."""

from __future__ import annotations

from pathlib import Path

import pytest

from swarm.blueprints.hybrid_moa.blueprint_hybrid_moa import HybridMoABlueprint


@pytest.mark.asyncio
async def test_hybrid_moa_blueprint_run(tmp_path: Path):
    bp = HybridMoABlueprint(blueprint_id="hybrid_moa")
    bp._config = {
        "moa": {
            "backend": "fake",
            "participants": ["analyst", "critic"],
            "presets": {
                "ci": {
                    "backend": "fake",
                    "participants": ["analyst", "critic"],
                    "fake_responses": {
                        "analyst": '{"claim":"yes bucket","confidence":0.9}',
                        "critic": '{"claim":"yes bucket+metrics","confidence":0.8}',
                    },
                }
            },
        }
    }
    bp.set_params({"preset": "ci", "workdir": str(tmp_path), "backend": "fake"})
    chunks = []
    async for c in bp.run([{"role": "user", "content": "Rate limit the API?"}]):
        chunks.append(c)
    final = chunks[-1]
    assert final.get("final") is True
    content = final["messages"][0]["content"]
    assert "bucket" in content.lower() or "MoA" in content or "decision" in content.lower()
    assert (tmp_path / "decision.md").is_file() or (tmp_path / "moa_determination.md").is_file()
    assert final["meta"].get("hybrid_moa") is True
