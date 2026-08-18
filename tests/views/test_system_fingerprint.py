"""Tests for system_fingerprint — naming which CLI(s) actually answered.

A blueprint yields a ``meta`` side-channel on its final chunk; the API views
render it into ``system_fingerprint`` (chat.completions + responses) so any
OpenAI client can read which backends + judge produced the answer.
"""

from __future__ import annotations

import sys

from swarm.blueprints.common import cli_fusion_support as support
from swarm.views.chat_views import backend_fingerprint

PY = sys.executable


# --- the pure helper -------------------------------------------------------

def test_fingerprint_falls_back_to_blueprint_id_without_meta():
    assert backend_fingerprint("cli_fusion", None) == "cli_fusion"
    assert backend_fingerprint("cli_agent", {}) == "cli_agent"


def test_fingerprint_renders_backends_and_judge():
    meta = support.backend_meta(["gemini", "claude", "grok"], judge="claude")
    assert backend_fingerprint("cli_fusion", meta) == "cli_fusion:gemini+claude+grok|judge=claude"


def test_fingerprint_backends_only_when_no_judge():
    meta = support.backend_meta(["grok"])
    assert backend_fingerprint("cli_agent", meta) == "cli_agent:grok"


def test_backend_meta_drops_empty_names():
    assert support.backend_meta(["grok", "", None], judge=None) == {"backends": ["grok"]}


# --- end-to-end through a blueprint ----------------------------------------

def _echo(tag: str) -> dict:
    return {"cmd": [PY, "-c", f"print({tag!r})", "{prompt}"], "parse": "text"}


async def test_cli_agent_emits_backend_meta_on_final_chunk():
    from swarm.blueprints.cli_agent.blueprint_cli_agent import CliAgentBlueprint

    cfg = {"cli_agents": {"grok": _echo("HI")}, "cli_fusion": {"default_cli": "grok"}}
    bp = CliAgentBlueprint(blueprint_id="cli_agent", config=cfg)
    bp.set_params({"cli": "grok"})
    final = None
    async for chunk in bp.run([{"role": "user", "content": "x"}]):
        if isinstance(chunk, dict) and chunk.get("final"):
            final = chunk
    assert final is not None
    assert final.get("meta") == {"backends": ["grok"]}
    # And the view helper renders it as expected.
    assert backend_fingerprint("cli_agent", final["meta"]) == "cli_agent:grok"


async def test_cli_fusion_emits_panel_and_judge_meta():
    """cli_fusion → MoA: meta.backends lists ok participants (no multi-writer judge)."""
    from swarm.blueprints.cli_fusion.blueprint_cli_fusion import CliFusionBlueprint

    bp = CliFusionBlueprint(config={})
    bp.set_params(
        {
            "participants": ["a", "b"],
            "fake_responses": {"a": "A:x", "b": "B:x"},
        }
    )
    meta = None
    async for chunk in bp.run([{"role": "user", "content": "x"}]):
        if isinstance(chunk, dict) and chunk.get("meta"):
            meta = chunk["meta"]
    assert meta is not None
    assert meta.get("moa") is True
    assert set(meta["backends"]) == {"a", "b"}
    # MoA does not emit a separate judge field (orchestrator owns determination).
    assert backend_fingerprint("cli_fusion", meta) == "cli_fusion:a+b"
