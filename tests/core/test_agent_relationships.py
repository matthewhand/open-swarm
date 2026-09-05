"""REQ-153 relationship edges — team↔agent / team↔team, not a global mesh."""

import pytest

from swarm.core.agent_relationships import (
    normalize_edge,
    normalize_edges,
    reset_relationships,
)


def test_canonicalizes_and_dedupes_undirected_edges():
    edges = normalize_edges(
        [
            {"from_kind": "team", "from_id": "ops", "to_kind": "team", "to_id": "office"},
            {"from_kind": "team", "from_id": "office", "to_kind": "team", "to_id": "ops"},
        ]
    )
    assert len(edges) == 1
    assert edges[0].from_id == "office"
    assert edges[0].to_id == "ops"


def test_rejects_agent_agent_mesh():
    with pytest.raises(ValueError, match="team"):
        normalize_edge({"from_kind": "agent", "from_id": "pat", "to_kind": "agent", "to_id": "ada"})


def test_rejects_self_edge():
    with pytest.raises(ValueError, match="itself"):
        normalize_edge({"from_kind": "team", "from_id": "office", "to_kind": "team", "to_id": "office"})


def test_reset_relationships_is_in_memory_only():
    reset_relationships([{"from_kind": "team", "from_id": "a", "to_kind": "agent", "to_id": "b"}])
    try:
        from swarm.core.agent_relationships import load_relationships

        loaded = load_relationships()
        assert len(loaded) == 1
        ends = {loaded[0].from_id, loaded[0].to_id}
        assert ends == {"a", "b"}
    finally:
        reset_relationships(None)
