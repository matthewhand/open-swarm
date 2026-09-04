"""Declarative openai-agents handoff graphs (REQ-156).

A graph is nodes plus directed ``handoff`` edges. Building the graph attaches
**only** those edges — that is the topology LLM-only freestyle cannot enforce.

Limit (document up front): programmatic handoff / as-tool graphs run inside
**API / blueprint** agents. CLI and remote harnesses stay native sessions; they
can sit on a mixed team but cannot be *injected* into this graph as edge
sources.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GRAPH_VARIANTS = ("forced-sequence", "circular-skeptic")
NODE_KINDS = ("api", "cli", "remote")
EDGE_CHANNELS = ("handoff", "as_tool")

EXAMPLE_PACK_RELATIVE = Path("docs") / "examples" / "openai-agents-handoff-graphs"

PIPELINE_GRAPH_ID = "sdlc-pipeline"
SKEPTIC_LOOP_GRAPH_ID = "sdlc-skeptic-loop"

DEMO_ROSTER_IDS = (
    "demo-sdlc-pipeline",
    "demo-sdlc-skeptic-loop",
    "demo-bridge",
    "demo-harness-kinds",
)


def repo_root() -> Path:
    """Walk up from this file to the checkout that holds the example pack."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / EXAMPLE_PACK_RELATIVE).is_dir() and (parent / "pyproject.toml").is_file():
            return parent
    return here.parents[3] if len(here.parents) > 3 else here.parent


def example_pack_dir() -> Path:
    return repo_root() / EXAMPLE_PACK_RELATIVE


@dataclass(frozen=True)
class HandoffNode:
    """One seat in a programmatic graph (API) or a mixed-team placeholder."""

    id: str
    name: str
    role: str = "default"
    kind: str = "api"
    instructions: str = ""


@dataclass(frozen=True)
class HandoffEdge:
    """Directed programmatic edge. ``channel`` is handoff or as_tool."""

    source: str
    target: str
    channel: str = "handoff"


@dataclass(frozen=True)
class HandoffGraph:
    """Validated graph spec used to wire openai-agents ``Agent.handoffs``."""

    id: str
    name: str
    variant: str
    entry: str
    nodes: tuple[HandoffNode, ...]
    edges: tuple[HandoffEdge, ...]
    description: str = ""

    def node_ids(self) -> tuple[str, ...]:
        return tuple(n.id for n in self.nodes)

    def node_map(self) -> dict[str, HandoffNode]:
        return {n.id: n for n in self.nodes}

    def declared_edges(self, *, channel: str = "handoff") -> frozenset[tuple[str, str]]:
        return frozenset(
            (e.source, e.target) for e in self.edges if e.channel == channel
        )

    def outgoing(self, source: str, *, channel: str = "handoff") -> tuple[str, ...]:
        return tuple(
            e.target for e in self.edges if e.source == source and e.channel == channel
        )


def _require_str(raw: dict[str, Any], key: str, *, allow_empty: bool = False) -> str:
    value = raw.get(key)
    if value is None:
        raise ValueError(f"Missing {key!r}.")
    text = str(value).strip()
    if not text and not allow_empty:
        raise ValueError(f"{key!r} must be a non-empty string.")
    return text


def normalize_node(raw: Any) -> HandoffNode:
    if not isinstance(raw, dict):
        raise ValueError("Each node must be an object.")
    node_id = _require_str(raw, "id")
    name = str(raw.get("name") or node_id).strip() or node_id
    kind = str(raw.get("kind") or "api").strip().lower()
    if kind not in NODE_KINDS:
        raise ValueError(f"Node {node_id!r} kind must be one of {', '.join(NODE_KINDS)}.")
    role = str(raw.get("role") or "default").strip() or "default"
    instructions = str(raw.get("instructions") or "").strip()
    return HandoffNode(
        id=node_id,
        name=name,
        role=role,
        kind=kind,
        instructions=instructions,
    )


def normalize_edge(raw: Any) -> HandoffEdge:
    if not isinstance(raw, dict):
        raise ValueError("Each edge must be an object.")
    source = str(raw.get("from") or raw.get("source") or "").strip()
    target = str(raw.get("to") or raw.get("target") or "").strip()
    if not source or not target:
        raise ValueError("Each edge needs from/to (or source/target).")
    channel = str(raw.get("channel") or "handoff").strip().lower()
    if channel not in EDGE_CHANNELS:
        raise ValueError(f"Edge channel must be one of {', '.join(EDGE_CHANNELS)}.")
    return HandoffEdge(source=source, target=target, channel=channel)


def normalize_graph(raw: dict[str, Any]) -> HandoffGraph:
    """Validate a graph document. Raises ValueError on a bad spec."""
    if not isinstance(raw, dict):
        raise ValueError("Graph must be an object.")
    graph_id = _require_str(raw, "id")
    name = str(raw.get("name") or graph_id).strip() or graph_id
    variant = str(raw.get("variant") or "").strip()
    if variant not in GRAPH_VARIANTS:
        raise ValueError(f"variant must be one of {', '.join(GRAPH_VARIANTS)}.")
    entry = _require_str(raw, "entry")
    nodes_in = raw.get("nodes")
    edges_in = raw.get("edges")
    if not isinstance(nodes_in, list) or not nodes_in:
        raise ValueError("nodes must be a non-empty array.")
    if not isinstance(edges_in, list):
        raise ValueError("edges must be an array.")
    nodes = tuple(normalize_node(n) for n in nodes_in)
    ids = [n.id for n in nodes]
    if len(ids) != len(set(ids)):
        raise ValueError("Node ids must be unique.")
    if entry not in ids:
        raise ValueError(f"entry {entry!r} is not a node id.")
    edges = tuple(normalize_edge(e) for e in edges_in)
    known = set(ids)
    for edge in edges:
        if edge.source not in known or edge.target not in known:
            raise ValueError(
                f"Edge {edge.source}->{edge.target} references an unknown node."
            )
        if edge.source == edge.target:
            raise ValueError(f"Self-loop is not allowed: {edge.source}.")
        source_kind = next(n.kind for n in nodes if n.id == edge.source)
        if source_kind != "api":
            raise ValueError(
                f"Programmatic {edge.channel} edges may only start from kind=api "
                f"(got {source_kind!r} on {edge.source!r}). CLI/remote stay native."
            )
    return HandoffGraph(
        id=graph_id,
        name=name,
        variant=variant,
        entry=entry,
        nodes=nodes,
        edges=edges,
        description=str(raw.get("description") or "").strip(),
    )


def load_graph(path: str | Path) -> HandoffGraph:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} root must be an object.")
    return normalize_graph(payload)


def load_example_graph(graph_id: str) -> HandoffGraph:
    path = example_pack_dir() / f"{graph_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Example graph not found: {path}")
    return load_graph(path)


def load_example_roster(roster_id: str) -> dict[str, Any]:
    path = example_pack_dir() / f"{roster_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Example roster not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} root must be an object.")
    return payload


def graph_to_json(graph: HandoffGraph) -> dict[str, Any]:
    return {
        "id": graph.id,
        "name": graph.name,
        "variant": graph.variant,
        "entry": graph.entry,
        "description": graph.description,
        "nodes": [
            {
                "id": n.id,
                "name": n.name,
                "role": n.role,
                "kind": n.kind,
                "instructions": n.instructions,
            }
            for n in graph.nodes
        ],
        "edges": [
            {"from": e.source, "to": e.target, "channel": e.channel} for e in graph.edges
        ],
    }


def _default_instructions(node: HandoffNode, graph: HandoffGraph) -> str:
    if node.instructions:
        return node.instructions
    targets = graph.outgoing(node.id)
    if not targets:
        return (
            f"You are {node.name}. You have no further programmatic handoff. "
            "Finish the work for this seat and stop."
        )
    dest = ", ".join(targets)
    return (
        f"You are {node.name}. When your seat is done, hand off only to: {dest}. "
        "Do not skip ahead or invent other seats."
    )


def build_agents(graph: HandoffGraph) -> dict[str, Any]:
    """Create openai-agents ``Agent`` objects with **only** declared handoffs."""
    from agents import Agent, handoff

    agents: dict[str, Any] = {}
    for node in graph.nodes:
        if node.kind != "api":
            continue
        agents[node.id] = Agent(
            name=node.id,
            instructions=_default_instructions(node, graph),
        )
    for node in graph.nodes:
        if node.id not in agents:
            continue
        targets = [
            agents[target]
            for target in graph.outgoing(node.id)
            if target in agents
        ]
        agents[node.id].handoffs = [handoff(target) for target in targets]
    return agents


def live_edges(agents: dict[str, Any]) -> frozenset[tuple[str, str]]:
    """Read ``Agent.handoffs`` (``Handoff.agent_name``) back into edge pairs."""
    found: set[tuple[str, str]] = set()
    for source, agent in agents.items():
        for item in getattr(agent, "handoffs", None) or []:
            target = getattr(item, "agent_name", None)
            if target:
                found.add((str(source), str(target)))
    return frozenset(found)


def assert_edges_match(graph: HandoffGraph, agents: dict[str, Any]) -> None:
    """Raise AssertionError when live handoffs differ from the declared graph."""
    declared = graph.declared_edges()
    live = live_edges(agents)
    if live != declared:
        extra = sorted(live - declared)
        missing = sorted(declared - live)
        raise AssertionError(
            f"Handoff edges mismatch for {graph.id}: extra={extra} missing={missing}"
        )


def format_graph(graph: HandoffGraph, *, live: Iterable[tuple[str, str]] | None = None) -> str:
    """Human status dump used by the blueprint and :8001 prove step."""
    edges = sorted(live if live is not None else graph.declared_edges())
    lines = [
        f"{graph.name} ({graph.id})",
        f"variant: {graph.variant}",
        f"entry: {graph.entry}",
        f"nodes: {', '.join(graph.node_ids())}",
        "handoff edges (programmatic; API/blueprint only):",
    ]
    if edges:
        lines.extend(f"  {src} -> {dst}" for src, dst in edges)
    else:
        lines.append("  (none)")
    lines.append(
        "CLI and remote harnesses stay native — they are not edge sources "
        "in this graph."
    )
    if graph.description:
        lines.append(graph.description)
    return "\n".join(lines)


def merge_demo_rosters(
    existing: dict[str, Any] | None,
    rosters: Iterable[dict[str, Any]],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Additive merge. Only writes demo-* ids; never deletes other rosters."""
    merged = dict(existing or {})
    for roster in rosters:
        if not isinstance(roster, dict):
            raise ValueError("Each roster must be an object.")
        rid = str(roster.get("id") or "").strip()
        if not rid.startswith("demo-"):
            raise ValueError(f"Refusing to seed non-demo roster id {rid!r}.")
        if rid in merged and not overwrite:
            continue
        merged[rid] = roster
    return merged


def load_demo_rosters() -> list[dict[str, Any]]:
    return [load_example_roster(rid) for rid in DEMO_ROSTER_IDS]


def seed_demo_rosters(
    dest: Path,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Write labeled Demo rosters into a ``team_rosters.json`` path.

    Additive. No secrets. Does not touch ``teams.json`` or ``.env``.
    """
    dest = Path(dest)
    existing: dict[str, Any] = {}
    if dest.is_file() and dest.stat().st_size:
        parsed = json.loads(dest.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError(f"{dest} root must be an object.")
        existing = parsed
    merged = merge_demo_rosters(existing, load_demo_rosters(), overwrite=overwrite)
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return merged


__all__ = [
    "DEMO_ROSTER_IDS",
    "HandoffEdge",
    "HandoffGraph",
    "HandoffNode",
    "PIPELINE_GRAPH_ID",
    "SKEPTIC_LOOP_GRAPH_ID",
    "assert_edges_match",
    "build_agents",
    "example_pack_dir",
    "format_graph",
    "graph_to_json",
    "live_edges",
    "load_demo_rosters",
    "load_example_graph",
    "load_example_roster",
    "load_graph",
    "merge_demo_rosters",
    "normalize_graph",
    "repo_root",
    "seed_demo_rosters",
]
