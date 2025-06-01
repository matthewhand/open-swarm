import pytest
from unittest.mock import MagicMock, patch
from agents.mcp import MCPServer # Assuming this is the correct MCPServer
from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint
from agents import Agent as ExpectedAgentClass # For type checking

def setup_mcp_mock(name_str: str, is_disabled: bool = False) -> MagicMock:
    mock = MagicMock(spec=MCPServer)
    mock.name = name_str
    mock.disabled = is_disabled
    return mock

def test_agent_mcp_assignment():
    memory_mock_for_writer = setup_mcp_mock(name_str="memory", is_disabled=False)
    blueprint_known_mcps = [memory_mock_for_writer]
    agent_mcp_assignments_config_input = { # Renamed to avoid confusion with blueprint's internal attribute
        "WriterAgent": [memory_mock_for_writer],
    }
   
    blueprint = GeeseBlueprint(
        blueprint_id="test_writer_assignment_isolated",
        mcp_servers=blueprint_known_mcps,
        agent_mcp_assignments_config=agent_mcp_assignments_config_input, 
    )

    writer = blueprint.writer_agent
    assert writer is not None, "Writer agent was not created"
    print(f"DEBUG_TEST: Type of writer agent: {type(writer)}")
    assert isinstance(writer, ExpectedAgentClass), f"Writer agent is not of type ExpectedAgentClass, but {type(writer)}"
    
    print(f"DEBUG_TEST: writer.__dict__ keys: {writer.__dict__.keys() if hasattr(writer, '__dict__') else 'NO_DICT'}")

    writer_mcps_attr = getattr(writer, "mcp_servers", "ATTR_NOT_FOUND")
    print(f"DEBUG_TEST: writer.mcp_servers raw attribute = {writer_mcps_attr}")

    assert "mcp_servers" in writer.__dict__, "mcp_servers not in writer.__dict__" # More direct check

    if writer_mcps_attr != "ATTR_NOT_FOUND":
        print(f"DEBUG_TEST: writer.mcp_servers type = {type(writer_mcps_attr)}")
        if isinstance(writer_mcps_attr, list):
            print(f"DEBUG_TEST: writer.mcp_servers length = {len(writer_mcps_attr)}")
            if writer_mcps_attr:
                print(f"DEBUG_TEST: writer.mcp_servers[0] object = {writer_mcps_attr[0]}")
                print(f"DEBUG_TEST: writer.mcp_servers[0] name = {getattr(writer_mcps_attr[0], 'name', 'NO_NAME_ATTR')}")
                print(f"DEBUG_TEST: writer.mcp_servers[0] is instance of MCPServer = {isinstance(writer_mcps_attr[0], MCPServer)}")
        else:
            print(f"DEBUG_TEST: writer.mcp_servers is not a list.")

    assert writer_mcps_attr != "ATTR_NOT_FOUND", "mcp_servers attribute missing from writer agent via getattr"
    assert isinstance(writer_mcps_attr, list), f"writer.mcp_servers is not a list, it's a {type(writer_mcps_attr)}"

    assigned_mcps_writer_names = [m.name for m in writer_mcps_attr if hasattr(m, 'name')]
    assert set(assigned_mcps_writer_names) == {"memory"}


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

    coordinator = blueprint.coordinator_agent
    assert coordinator is not None, "Coordinator agent not created"
    assert isinstance(coordinator, ExpectedAgentClass), f"Coordinator agent is not of type ExpectedAgentClass, but {type(coordinator)}"
    
    coordinator_mcps_attr = getattr(coordinator, "mcp_servers", [])
    assigned_mcps_coordinator_names = [m.name for m in coordinator_mcps_attr if hasattr(m, 'name')]
    assert set(assigned_mcps_coordinator_names) == {"memory"}

    writer_mcps_attr = getattr(blueprint.writer_agent, "mcp_servers", [])
    assigned_mcps_writer_names = [m.name for m in writer_mcps_attr if hasattr(m, 'name')]
    assert "memory" not in assigned_mcps_writer_names
