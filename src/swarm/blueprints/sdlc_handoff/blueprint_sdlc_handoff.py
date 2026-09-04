"""sdlc_handoff — forced BA → Engineer → Tester (and circular skeptic).

REQ-156 example blueprint. openai-agents ``handoff`` edges are the product:
each seat gets **only** the next hop. LLM-only freestyle cannot enforce that.

Variants:
    pipeline / forced-sequence   BA → Engineer → Tester (one-way)
    skeptic_loop / circular-skeptic   last skeptic punts back to Engineer

CLI and remote harnesses are **not** injected into this graph. They stay
native sessions and may sit on a mixed team (see the example pack).

Deterministic grammar (no LLM — same idea as ``software_dev``)::

    status | graph     print declared + live handoff edges
    variant <name>     switch pipeline vs skeptic_loop (also ``params.variant``)

Config block ``sdlc_handoff`` (optional)::

    {"sdlc_handoff": {"variant": "pipeline"}}
"""

from __future__ import annotations

import logging
import os
from typing import Any, ClassVar

from swarm.blueprints.common import cli_fusion_support as support
from swarm.core.blueprint_base import BlueprintBase
from swarm.core.handoff_graph import (
    PIPELINE_GRAPH_ID,
    SKEPTIC_LOOP_GRAPH_ID,
    assert_edges_match,
    build_agents,
    format_graph,
    live_edges,
    load_example_graph,
)

logger = logging.getLogger(__name__)

VARIANT_ALIASES = {
    "pipeline": PIPELINE_GRAPH_ID,
    "forced-sequence": PIPELINE_GRAPH_ID,
    "forced_sequence": PIPELINE_GRAPH_ID,
    PIPELINE_GRAPH_ID: PIPELINE_GRAPH_ID,
    "skeptic_loop": SKEPTIC_LOOP_GRAPH_ID,
    "skeptic-loop": SKEPTIC_LOOP_GRAPH_ID,
    "circular": SKEPTIC_LOOP_GRAPH_ID,
    "circular-skeptic": SKEPTIC_LOOP_GRAPH_ID,
    "circular_skeptic": SKEPTIC_LOOP_GRAPH_ID,
    SKEPTIC_LOOP_GRAPH_ID: SKEPTIC_LOOP_GRAPH_ID,
}


class SdlcHandoffBlueprint(BlueprintBase):
    """API-only SDLC handoff graph: forced pipeline or circular skeptic."""

    metadata: ClassVar[dict[str, Any]] = {
        "name": "sdlc_handoff",
        "title": "SDLC handoff graph (BA / Engineer / Tester)",
        "description": (
            "Example openai-agents handoff graph: forced BA → Engineer → Tester, "
            "plus a circular skeptic that can punt back. API/blueprint only — "
            "CLI and remote harnesses stay native. Not extra Grok Bot seats."
        ),
        "version": "0.1.0",
        "author": "Open Swarm Team",
        "tags": ["sdlc", "handoff", "openai-agents", "demo", "ba", "engineer", "tester"],
        "aliases": ["sdlc-handoff", "sdlc_pipeline"],
        "required_mcp_servers": [],
        "env_vars": [],
        "agents": [
            {"name": "ba", "role": "default", "seat": "ba"},
            {"name": "engineer", "role": "default", "seat": "engineer"},
            {"name": "tester", "role": "default", "seat": "tester"},
            {"name": "skeptic", "role": "skeptic", "seat": "skeptic"},
        ],
    }

    def __init__(self, blueprint_id: str = "sdlc_handoff", config=None, config_path=None, **kwargs):
        super().__init__(blueprint_id, config=config, config_path=config_path, **kwargs)
        self._params: dict[str, Any] = {}
        self._agents: dict[str, Any] = {}
        self._graph_id: str = PIPELINE_GRAPH_ID

    def set_params(self, params: dict[str, Any] | None) -> None:
        self._params = dict(params or {})
        self._agents = {}

    def _cfg(self) -> dict[str, Any]:
        block = (self._config or {}).get("sdlc_handoff") or {}
        return block if isinstance(block, dict) else {}

    def resolve_variant(self) -> str:
        raw = (
            self._params.get("variant")
            or self._cfg().get("variant")
            or PIPELINE_GRAPH_ID
        )
        key = str(raw).strip().lower().replace(" ", "-")
        if key not in VARIANT_ALIASES:
            raise ValueError(
                f"Unknown sdlc_handoff variant {raw!r}. "
                f"Use pipeline or skeptic_loop."
            )
        return VARIANT_ALIASES[key]

    def graph(self):
        graph_id = self.resolve_variant()
        self._graph_id = graph_id
        return load_example_graph(graph_id)

    def _build_agents(self) -> dict[str, Any]:
        if self._agents:
            return self._agents
        graph = self.graph()
        self._agents = build_agents(graph)
        return self._agents

    def _last_user_text(self, messages: list[dict[str, Any]]) -> str:
        for m in reversed(messages or []):
            if (m.get("role") or "user") == "user" and m.get("content"):
                return str(m["content"]).strip()
        return support.render_prompt(messages).strip()

    def _parse(self, messages: list[dict[str, Any]]) -> tuple[str, str]:
        params = dict(self._params)
        action = str(params.get("action") or "").strip().lower()
        text = self._last_user_text(messages)
        if action:
            return action, text
        parts = text.split(None, 1)
        head = (parts[0].lower() if parts else "status").rstrip(":")
        rest = parts[1] if len(parts) > 1 else ""
        if head in ("status", "graph", "edges", "who"):
            return "graph", rest
        if head == "variant" and rest:
            self._params["variant"] = rest.strip()
            self._agents = {}
            return "graph", rest
        return "graph", text

    def _status_text(self) -> str:
        graph = self.graph()
        agents = self._build_agents()
        live = live_edges(agents)
        assert_edges_match(graph, agents)
        return format_graph(graph, live=live)

    async def run(self, messages: list[dict[str, Any]], **_kwargs) -> Any:
        _action, _text = self._parse(messages)
        test_mode = os.environ.get("SWARM_TEST_MODE", "").lower() in ("1", "true", "yes")
        # This blueprint's job is the graph, not a live Runner conversation.
        # Always return the enforced edges (LLM freestyle is the anti-pattern).
        try:
            body = self._status_text()
        except Exception as exc:
            logger.warning("sdlc_handoff graph status failed: %s", exc)
            body = f"sdlc_handoff: could not load example graph ({exc})"
            if not test_mode:
                body += "\nCLI/remote harnesses stay native; only API gets this graph."
        yield support.message_chunk(
            body,
            final=True,
            meta=support.backend_meta(["sdlc_handoff", self._graph_id]),
        )


if __name__ == "__main__":
    import asyncio

    async def _main() -> None:
        bp = SdlcHandoffBlueprint()
        async for chunk in bp.run([{"role": "user", "content": "graph"}]):
            msgs = chunk.get("messages") if isinstance(chunk, dict) else None
            if msgs:
                print(msgs[0].get("content") or "")

    asyncio.run(_main())
