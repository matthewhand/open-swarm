"""Stewie blueprint: hermetic SWARM_TEST_MODE coverage."""

from __future__ import annotations

import pytest

from swarm.blueprints.stewie.blueprint_stewie import StewieBlueprint
from swarm.core.blueprint_base import BlueprintBase


async def _collect(gen):
    return [c async for c in gen]


def _final_content(chunks):
    text = None
    for c in chunks:
        msgs = c.get("messages") if isinstance(c, dict) else None
        if msgs and msgs[0].get("content") is not None:
            text = msgs[0]["content"]
    return text


@pytest.fixture(autouse=True)
def _test_mode(monkeypatch):
    monkeypatch.setenv("SWARM_TEST_MODE", "1")


def test_metadata_and_subclass():
    assert issubclass(StewieBlueprint, BlueprintBase)
    assert StewieBlueprint.metadata.get("title")
    assert "wordpress" in (StewieBlueprint.metadata.get("tags") or [])
    # dirname id remains the discoverable model id
    bp = StewieBlueprint(blueprint_id="stewie")
    assert bp.blueprint_id == "stewie"


@pytest.mark.asyncio
async def test_test_mode_echoes_instruction():
    bp = StewieBlueprint(blueprint_id="stewie")
    chunks = await _collect(bp.run([{"role": "user", "content": "ping"}]))
    text = _final_content(chunks)
    assert text is not None
    assert "[TEST-MODE]" in text
    assert "ping" in text
    assert "Stewie" in text or "deuce" in text.lower()
