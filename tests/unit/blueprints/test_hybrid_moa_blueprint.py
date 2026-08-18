"""Unit tests for hybrid_moa blueprint."""

from __future__ import annotations

from pathlib import Path

import pytest

from swarm.blueprints.hybrid_moa.blueprint_hybrid_moa import HybridMoABlueprint


@pytest.mark.asyncio
async def test_hybrid_moa_blueprint_run(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(tmp_path))
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
    bp.set_params({"preset": "ci", "workdir": "hybrid-run", "backend": "fake"})
    chunks = []
    async for c in bp.run([{"role": "user", "content": "Rate limit the API?"}]):
        chunks.append(c)
    final = chunks[-1]
    assert final.get("final") is True
    content = final["messages"][0]["content"]
    assert "bucket" in content.lower() or "MoA" in content or "decision" in content.lower()
    ws = tmp_path / "hybrid-run"
    assert (ws / "decision.md").is_file() or (ws / "moa_determination.md").is_file()
    assert final["meta"].get("hybrid_moa") is True


@pytest.mark.asyncio
async def test_hybrid_moa_rejects_workdir_outside_root(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SWARM_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    monkeypatch.delenv("ALLOW_UNRESTRICTED_WORKDIR", raising=False)
    bp = HybridMoABlueprint(blueprint_id="hybrid_moa")
    bp._config = {"moa": {"backend": "fake", "participants": ["analyst"]}}
    bp.set_params({"workdir": str(tmp_path / "escape"), "backend": "fake"})
    chunks = []
    async for c in bp.run([{"role": "user", "content": "hi"}]):
        chunks.append(c)
    content = chunks[-1]["messages"][0]["content"]
    assert "outside the workspaces root" in content
    assert not (tmp_path / "escape").exists()
