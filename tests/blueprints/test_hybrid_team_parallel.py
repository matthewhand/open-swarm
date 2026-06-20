"""Parallel delegation execution in hybrid_team.

Delegations run concurrently on a ThreadPoolExecutor with per-task timeout and
error isolation. Deterministic under SWARM_TEST_MODE (the _run_delegation stub).
"""
from __future__ import annotations

import time

import pytest

from swarm.blueprints.hybrid_team.blueprint_hybrid_team import HybridTeamBlueprint

CONFIG = {"llm": {"default": {"provider": "openai", "model": "d"}}}


def _bp() -> HybridTeamBlueprint:
    return HybridTeamBlueprint(config=CONFIG)


@pytest.fixture(autouse=True)
def _test_mode(monkeypatch):
    monkeypatch.setenv("SWARM_TEST_MODE", "1")


async def test_executes_all_delegations(monkeypatch):
    dels = [
        {"role": "agent", "task": "a"},
        {"role": "auxiliary", "task": "b"},
        {"role": "orchestration", "task": "c"},
    ]
    results = [ev async for ev in _bp()._execute_delegations(dels)]
    assert len(results) == 3
    assert all(ev["status"] == "completed" for ev in results)
    by_role = {ev["role"]: ev for ev in results}
    assert by_role["agent"]["result"] == "[agent] a"
    assert by_role["auxiliary"]["result"] == "[auxiliary] b"
    # every result carries the observability fields
    for ev in results:
        assert set(("role", "task", "status", "result", "model_used")) <= set(ev)


async def test_runs_in_parallel_not_serial(monkeypatch):
    # Make each delegation block ~0.4s; 3 in parallel (pool=4) finish near 0.4s,
    # well under the 1.2s a serial run takes. Zero the launch stagger (a separate
    # rate-limit concern) so this isolates the parallelism.
    async def slow(d):
        await __import__("asyncio").sleep(0.4)
        return f"[{d['role']}] {d['task']}"

    bp = _bp()
    monkeypatch.setattr(bp, "_run_delegation", slow)
    monkeypatch.setattr(HybridTeamBlueprint, "_DELEGATION_LAUNCH_DELAY_S", 0.0)
    dels = [{"role": "agent", "task": str(i)} for i in range(3)]
    started = time.monotonic()
    results = [ev async for ev in bp._execute_delegations(dels)]
    elapsed = time.monotonic() - started
    assert len(results) == 3 and all(ev["status"] == "completed" for ev in results)
    assert elapsed < 0.9, f"expected parallel (<0.9s), took {elapsed:.2f}s"


async def test_error_isolation(monkeypatch):
    async def maybe_boom(d):
        if d["role"] == "agent":
            raise RuntimeError("boom")
        return f"[{d['role']}] {d['task']}"

    bp = _bp()
    monkeypatch.setattr(bp, "_run_delegation", maybe_boom)
    dels = [{"role": "agent", "task": "x"}, {"role": "auxiliary", "task": "y"}]
    results = {ev["role"]: ev async for ev in bp._execute_delegations(dels)}
    assert results["agent"]["status"] == "failed"
    assert "boom" in results["agent"]["error"]
    assert results["auxiliary"]["status"] == "completed"  # one failure didn't kill the other


async def test_per_delegation_timeout(monkeypatch):
    async def hang(d):
        await __import__("asyncio").sleep(5)
        return "never"

    bp = _bp()
    monkeypatch.setattr(bp, "_run_delegation", hang)
    monkeypatch.setattr(HybridTeamBlueprint, "_DELEGATION_TIMEOUT_S", 0.3)
    results = [ev async for ev in bp._execute_delegations([{"role": "agent", "task": "x"}])]
    assert results[0]["status"] == "failed"
    assert "timed out" in results[0]["error"]
