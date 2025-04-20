import pytest
from unittest.mock import MagicMock, patch
from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint

def test_agent_mcp_assignment():
    mcp_servers = {
        "filesystem": {"name": "filesystem", "disabled": False},
        "semantic_search": {"name": "semantic_search", "disabled": False},
        "disabled_mcp": {"name": "disabled_mcp", "disabled": True},
    }
    agent_mcp_assignments = {
        "GooseCoordinator": ["filesystem", "semantic_search"],
        "WriterAgent": ["semantic_search"],
        "EditorAgent": [],
    }
    blueprint = GeeseBlueprint(
        blueprint_id="test",
        mcp_servers=mcp_servers,
        agent_mcp_assignments=agent_mcp_assignments,
    )
    # Assert coordinator agent has both MCPs
    coordinator = blueprint.agents["GooseCoordinator"]
    assigned_mcps = [m.get("name") for m in getattr(coordinator, "mcp_servers", [])]
    assert set(assigned_mcps) == {"filesystem", "semantic_search"}
    # WriterAgent has only semantic_search
    writer = blueprint.agents["WriterAgent"]
    assigned_mcps = [m.get("name") for m in getattr(writer, "mcp_servers", [])]
    assert assigned_mcps == ["semantic_search"]
    # EditorAgent has none (local only)
    editor = blueprint.agents["EditorAgent"]
    assert getattr(editor, "mcp_servers", []) == []

def test_agent_mcp_assignment_cli_override(monkeypatch):
    mcp_servers = {
        "filesystem": {"name": "filesystem", "disabled": False},
        "semantic_search": {"name": "semantic_search", "disabled": False},
    }
    agent_mcp_assignments = {
        "GooseCoordinator": ["filesystem"],
    }
    cli_assignments = {"GooseCoordinator": ["semantic_search"]}
    # Simulate CLI override
    blueprint = GeeseBlueprint(
        blueprint_id="test",
        mcp_servers=mcp_servers,
        agent_mcp_assignments=cli_assignments,
    )
    coordinator = blueprint.agents["GooseCoordinator"]
    assigned_mcps = [m.get("name") for m in getattr(coordinator, "mcp_servers", [])]
    assert assigned_mcps == ["semantic_search"]
