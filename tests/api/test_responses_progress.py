"""Responses worker captures per-delegation progress from blueprint chunks.

A blueprint that emits ``delegation_progress`` chunks (carrying a ``delegation``
payload) has those entries surfaced via ``_consume_blueprint``'s on_progress hook
— which the async worker persists into the record's ``progress`` array.
"""
from __future__ import annotations

from swarm.views.responses_views import _consume_blueprint


class _FakeBlueprint:
    async def run(self, messages, stream=False):
        # two parallel delegations report in, then a final answer
        yield {
            "type": "delegation_progress", "content": "_• agent completed_",
            "delegation": {"role": "agent", "status": "completed", "result": "coded it", "model_used": "qwen3.5"},
        }
        yield {
            "type": "delegation_progress", "content": "_• auxiliary failed_",
            "delegation": {"role": "auxiliary", "status": "failed", "error": "boom", "model_used": "qwen3.5"},
        }
        yield {"messages": [{"role": "assistant", "content": "final answer"}], "final": True}


async def test_consume_blueprint_streams_delegation_progress():
    captured: list[dict] = []
    answer, meta = await _consume_blueprint(_FakeBlueprint(), [], on_progress=captured.append)

    assert answer == "final answer"  # delegation chunks don't pollute the answer
    assert [c["role"] for c in captured] == ["agent", "auxiliary"]
    assert captured[0]["status"] == "completed" and captured[0]["result"] == "coded it"
    assert captured[1]["status"] == "failed" and captured[1]["error"] == "boom"
    assert captured[0]["model_used"] == "qwen3.5"


async def test_consume_blueprint_no_progress_callback_is_fine():
    # Without on_progress the same blueprint still yields its final answer.
    answer, _ = await _consume_blueprint(_FakeBlueprint(), [])
    assert answer == "final answer"
