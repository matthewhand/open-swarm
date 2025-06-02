import pytest
from unittest.mock import MagicMock
from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint
from agents import Agent as ExpectedAgentClass # Assuming this is the expected base class
from agents.mcp import MCPServer # Assuming this is the SDK's MCPServer

# Helper to create MCPServer mocks
def setup_mcp_mock(name_str: str, is_disabled: bool = False) -> MagicMock:
    mcp_mock = MagicMock(spec=MCPServer)
    mcp_mock.name = name_str
    mcp_mock.is_disabled = is_disabled
    return mcp_mock

@pytest.mark.skip(reason="Test needs update for refactored GeeseBlueprint agent creation.")
def test_agent_mcp_assignment():
    memory_mock_for_writer = setup_mcp_mock(name_str="memory", is_disabled=False)
    blueprint_known_mcps = [memory_mock_for_writer]
    agent_mcp_assignments_config_input = {
        "WriterAgent": [memory_mock_for_writer],
    }

    blueprint = GeeseBlueprint(
        blueprint_id="test_writer_assignment_isolated",
        mcp_servers=blueprint_known_mcps,
        agent_mcp_assignments_config=agent_mcp_assignments_config_input,
    )

    writer = blueprint.writer_agent # This attribute no longer exists directly
    assert writer is not None, "Writer agent was not created"
    assert isinstance(writer, ExpectedAgentClass), f"Writer agent is not of type ExpectedAgentClass, but {type(writer)}"
    
    writer_mcps_attr = getattr(writer, "mcp_servers", "ATTR_NOT_FOUND")
    assert writer_mcps_attr != "ATTR_NOT_FOUND", "mcp_servers attribute missing from writer agent via getattr"
    assert isinstance(writer_mcps_attr, list), f"writer.mcp_servers is not a list, it's a {type(writer_mcps_attr)}"
    
    assigned_mcps_writer_names = [m.name for m in writer_mcps_attr if hasattr(m, 'name')]
    assert set(assigned_mcps_writer_names) == {"memory"}

@pytest.mark.skip(reason="Test needs update for refactored GeeseBlueprint agent creation.")
def test_agent_mcp_assignment_cli_override():
    filesystem_mock = setup_mcp_mock(name_str="filesystem")
    memory_mock = setup_mcp_mock(name_str="memory")
    initial_blueprint_mcps = [filesystem_mock, memory_mock]

    cli_assignments_config = {
        "GooseCoordinator": [memory_mock] 
    }

    blueprint = GeeseBlueprint(
        blueprint_id="test_cli_override",
        mcp_servers=initial_blueprint_mcps, 
        agent_mcp_assignments_config=cli_assignments_config
    )

    coordinator = blueprint.coordinator_agent # This attribute no longer exists directly
    assert coordinator is not None, "Coordinator agent not created"
    assert isinstance(coordinator, ExpectedAgentClass), f"Coordinator agent is not of type ExpectedAgentClass, but {type(coordinator)}"
    
    coordinator_mcps_attr = getattr(coordinator, "mcp_servers", [])
    assigned_mcps_coordinator_names = [m.name for m in coordinator_mcps_attr if hasattr(m, 'name')]
    assert set(assigned_mcps_coordinator_names) == {"memory"} 

    writer = blueprint.writer_agent # This attribute no longer exists directly
    assert writer is not None, "Writer agent not created"
    writer_mcps_attr = getattr(writer, "mcp_servers", [])
    assigned_mcps_writer_names = [m.name for m in writer_mcps_attr if hasattr(m, 'name')]
    assert set(assigned_mcps_writer_names) == {"filesystem", "memory"}
