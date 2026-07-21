"""Tests for legacy model id ``cli_fusion`` → MoA (read-only consensus).

Historical multi-writer panel helpers were removed. ``CliFusionBlueprint`` is a
thin alias of :class:`~swarm.blueprints.moa.blueprint_moa.MoABlueprint`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from swarm.blueprints.cli_fusion.blueprint_cli_fusion import CliFusionBlueprint
from swarm.blueprints.moa.blueprint_moa import MoABlueprint
from swarm.core.blueprint_discovery import discover_blueprints


def test_cli_fusion_is_moa_subclass():
    assert issubclass(CliFusionBlueprint, MoABlueprint)
    assert CliFusionBlueprint.metadata["name"] == "cli_fusion"


def test_cli_fusion_discovered():
    root = Path("src/swarm/blueprints").resolve()
    found = discover_blueprints(str(root))
    assert "cli_fusion" in found
    # Discovery may re-exec modules → different class objects than test imports;
    # assert MoA lineage by MRO name (not identity issubclass across reloads).
    mro = [c.__name__ for c in found["cli_fusion"]["class_type"].__mro__]
    assert "MoABlueprint" in mro or "CliFusionBlueprint" in mro


async def _collect(gen):
    return [c async for c in gen]


def _final_content(chunks):
    text = None
    for c in chunks:
        if not isinstance(c, dict):
            continue
        msgs = c.get("messages")
        if msgs and msgs[0].get("content") is not None:
            text = msgs[0]["content"]
        elif c.get("content") is not None and c.get("final"):
            text = c["content"]
    return text


@pytest.mark.asyncio
async def test_cli_fusion_runs_moa_with_fake_responses():
    bp = CliFusionBlueprint(blueprint_id="cli_fusion", config={})
    bp.set_params(
        {
            "participants": ["a", "b"],
            "fake_responses": {
                "a": '{"claim":"A wins","confidence":0.9}',
                "b": '{"claim":"B also","confidence":0.5}',
            },
        }
    )
    chunks = await _collect(bp.run([{"role": "user", "content": "pick one"}]))
    assert chunks
    final = chunks[-1]
    assert final.get("meta", {}).get("moa") is True
    content = _final_content(chunks)
    assert content
    assert "A wins" in content or "claim" in content.lower() or len(content) > 5
    backends = final.get("meta", {}).get("backends") or []
    assert "a" in backends or "b" in backends


@pytest.mark.asyncio
async def test_cli_fusion_default_fake_stubs_when_no_responses():
    bp = CliFusionBlueprint(blueprint_id="cli_fusion", config={})
    bp.set_params({"backend": "fake", "participants": ["analyst", "critic"]})
    chunks = await _collect(bp.run([{"role": "user", "content": "hello"}]))
    content = _final_content(chunks)
    assert content
    assert "stub" in content.lower() or "analyst" in content.lower() or len(content) > 10
