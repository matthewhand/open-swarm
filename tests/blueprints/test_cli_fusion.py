"""Tests for the CLI Fusion blueprint (panel -> judge -> synthesize + master plan)."""

from __future__ import annotations

import json
import sys

import pytest

from swarm.blueprints.cli_fusion.blueprint_cli_fusion import (
    CliFusionBlueprint,
    _safe_json,
)

PY = sys.executable


def _echo(name_prefix: str) -> dict:
    return {"cmd": [PY, "-c", f"import sys; print('{name_prefix}:' + sys.argv[1])", "{prompt}"]}


def _judge_emitting(obj: dict) -> dict:
    # A "judge" CLI that ignores input and prints a fixed JSON analysis.
    payload = json.dumps(obj).replace("'", "\\'")
    return {"cmd": [PY, "-c", f"import sys; print('{payload}')", "{prompt}"]}


def _config(*, judge_obj=None, panel=("a", "b"), max_rounds=1, **fusion_extra) -> dict:
    agents = {"a": _echo("A"), "b": _echo("B")}
    fusion = {"presets": {"p": {"panel": list(panel)}}, "default_preset": "p", "max_rounds": max_rounds}
    if judge_obj is not None:
        agents["judge"] = _judge_emitting(judge_obj)
        fusion["presets"]["p"]["judge"] = "judge"
    fusion.update(fusion_extra)
    return {"cli_agents": agents, "cli_fusion": fusion}


async def _collect(gen):
    return [c async for c in gen]


def _final_content(chunks):
    text = None
    for c in chunks:
        msgs = c.get("messages") if isinstance(c, dict) else None
        if msgs and msgs[0].get("content") is not None:
            text = msgs[0]["content"]
    return text


def _all_text(chunks):
    return "\n".join(
        c["messages"][0]["content"]
        for c in chunks
        if isinstance(c, dict) and c.get("messages") and c["messages"][0].get("content")
    )


def _all_progress(chunks):
    return "\n".join(
        c["content"]
        for c in chunks
        if isinstance(c, dict) and c.get("type") == "fusion_progress"
    )


# --------------------------------------------------------------------------- #
# _safe_json
# --------------------------------------------------------------------------- #

def test_safe_json_plain():
    assert _safe_json('{"a": 1}') == {"a": 1}


def test_safe_json_embedded_in_prose():
    assert _safe_json('Here you go:\n{"a": 1}\nthanks') == {"a": 1}


def test_safe_json_garbage_returns_none():
    assert _safe_json("no json here") is None
    assert _safe_json("") is None


# --------------------------------------------------------------------------- #
# Fusion: single round
# --------------------------------------------------------------------------- #

async def test_fusion_no_agents():
    bp = CliFusionBlueprint(config={})
    chunks = await _collect(bp.run([{"role": "user", "content": "x"}]))
    assert "No CLI agents are configured" in _final_content(chunks)


async def test_fusion_judge_answer_used():
    cfg = _config(judge_obj={"answer": "SYNTHESIZED", "done": True})
    bp = CliFusionBlueprint(config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "q"}]))
    assert _final_content(chunks) == "SYNTHESIZED"
    assert chunks[-1].get("final") is True


async def test_fusion_fallback_without_judge():
    # No judge: synthesize falls back to the longest successful panel answer.
    cfg = _config(panel=("a", "b"))  # no judge_obj
    bp = CliFusionBlueprint(config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "hello"}]))
    final = _final_content(chunks)
    assert final in ("A:hello", "B:hello")


async def test_fusion_panel_runs_all_agents():
    cfg = _config(judge_obj={"answer": "ok", "done": True})
    bp = CliFusionBlueprint(config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "q"}]))
    assert "a, b" in _all_progress(chunks)  # progress line names both panelists


# --------------------------------------------------------------------------- #
# Fusion: master-plan loop
# --------------------------------------------------------------------------- #

async def test_fusion_multiround_runs_until_ceiling():
    # Judge always says not done -> loop should run max_rounds then stop.
    cfg = _config(judge_obj={"answer": "partial", "done": False, "next_step": "go again"}, max_rounds=2)
    bp = CliFusionBlueprint(config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "q"}]))
    progress = _all_progress(chunks)
    assert "Round 1/2" in progress
    assert "Round 2/2" in progress
    assert "next step" in progress.lower()
    assert chunks[-1].get("final") is True


async def test_fusion_stops_early_when_done():
    cfg = _config(judge_obj={"answer": "final", "done": True}, max_rounds=3)
    bp = CliFusionBlueprint(config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "q"}]))
    progress = _all_progress(chunks)
    assert "Round 1/3" in progress
    assert "Round 2/3" not in progress  # stopped after round 1


async def test_max_rounds_is_capped():
    cfg = _config(judge_obj={"answer": "x", "done": False}, max_rounds=999)
    bp = CliFusionBlueprint(config=cfg)
    # _max_rounds clamps to the ceiling
    assert bp._max_rounds({}, cfg["cli_fusion"]) == 5


# --------------------------------------------------------------------------- #
# Fusion: failure + recursion guard
# --------------------------------------------------------------------------- #

async def test_fusion_bounded_concurrency_still_runs_all():
    cfg = _config(judge_obj={"answer": "ok", "done": True}, panel=("a", "b"), max_concurrency=1)
    bp = CliFusionBlueprint(config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "q"}]))
    # Serialized launches still produce the synthesized answer and name both agents.
    assert _final_content(chunks) == "ok"
    assert "a, b" in _all_progress(chunks)


async def test_fusion_all_panel_fail():
    cfg = {
        "cli_agents": {"boom": {"cmd": [PY, "-c", "import sys; sys.exit(1)", "{prompt}"]}},
        "cli_fusion": {"presets": {"p": {"panel": ["boom"]}}, "default_preset": "p"},
    }
    bp = CliFusionBlueprint(config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "q"}]))
    assert "All CLI panelists failed" in _final_content(chunks)


async def test_recursion_guard_degrades(monkeypatch):
    monkeypatch.setenv("SWARM_CLI_FUSION_DEPTH", "1")
    cfg = _config(judge_obj={"answer": "should-not-be-used", "done": True}, panel=("a", "b"))
    bp = CliFusionBlueprint(config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "deep"}]))
    assert "Nested fusion detected" in _all_progress(chunks)
    # Degraded to single panelist 'a', judge skipped -> fallback answer from 'a'.
    assert _final_content(chunks) == "A:deep"


async def test_show_analysis_footer():
    cfg = _config(
        judge_obj={"answer": "core", "done": True, "consensus": ["x", "y"]},
        show_analysis=True,
    )
    bp = CliFusionBlueprint(config=cfg)
    chunks = await _collect(bp.run([{"role": "user", "content": "q"}]))
    final = _final_content(chunks)
    assert "core" in final
    assert "consensus" in final
