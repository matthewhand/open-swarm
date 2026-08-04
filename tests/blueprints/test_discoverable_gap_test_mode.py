"""Minimal SWARM_TEST_MODE instantiate+run for discoverable blueprints without
dedicated unit modules under tests/blueprints/.

Extends UAT coverage so gaps (gawd, poets, stewie, dynamic_team, etc.) still
get a hermetic run path. MoA-family blueprints are excluded here — they fail
discovery/import due to a circular import in swarm.core.moa (tracked separately).
"""

from __future__ import annotations

import inspect

import pytest

# Directory-style blueprint ids that are discoverable but lack a dedicated
# tests/blueprints/test_<name>*.py module (system/*.sh or unit/ only doesn't count).
GAP_BLUEPRINTS = (
    "chucks_angels",
    "dynamic_team",
    "gawd",
    "poets",
    "stewie",
    "whiskeytango_foxtrot",
)


@pytest.fixture(autouse=True)
def _test_mode(monkeypatch):
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-test-mode")


def _discover():
    from swarm.core.blueprint_discovery import discover_blueprints
    from swarm.settings import BLUEPRINT_DIRECTORY

    return discover_blueprints(str(BLUEPRINT_DIRECTORY))


async def _drain(result, limit: int = 30):
    if inspect.isasyncgen(result):
        chunks = []
        async for c in result:
            chunks.append(c)
            if len(chunks) >= limit:
                break
        return chunks
    if inspect.iscoroutine(result):
        return [await result]
    if inspect.isgenerator(result):
        chunks = []
        for c in result:
            chunks.append(c)
            if len(chunks) >= limit:
                break
        return chunks
    return [result]


@pytest.mark.asyncio
@pytest.mark.parametrize("blueprint_id", GAP_BLUEPRINTS)
async def test_gap_blueprint_instantiate_and_run(blueprint_id):
    discovered = _discover()
    assert blueprint_id in discovered, (
        f"{blueprint_id} not discoverable; keys={sorted(discovered)[:20]}..."
    )
    info = discovered[blueprint_id]
    cls = info["class_type"] if isinstance(info, dict) else info

    try:
        bp = cls(blueprint_id=blueprint_id)
    except TypeError:
        bp = cls()

    chunks = await _drain(bp.run([{"role": "user", "content": "ping"}]))
    assert chunks, f"{blueprint_id} produced no run output under SWARM_TEST_MODE"
