import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/swarm')))
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Assuming BlueprintBase and other necessary components are importable
# from blueprints.omniplex.blueprint_omniplex import OmniplexBlueprint
# from agents import Agent, Runner, RunResult, MCPServer

@pytest.fixture
def omniplex_blueprint_instance(tmp_path):
    """Fixture to create a mocked instance of OmniplexBlueprint."""
    mock_config = {
        'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}},
        'mcpServers': {
            'npx_server_1': {'command': 'npx something', 'args': []},
            'npx_server_2': {'command': ['/usr/bin/npx', 'another'], 'args': []},
            'uvx_server_1': {'command': ['uvx', 'run', 'tool'], 'args': []},
            'other_server': {'command': '/usr/local/bin/mytool', 'args': []},
            'memory': {'command': ['python', '-m', 'memory_server'], 'args': []}
        }
    }
    with patch('blueprints.omniplex.blueprint_omniplex.BlueprintBase._load_and_process_config', return_value=mock_config):
        from blueprints.omniplex.blueprint_omniplex import OmniplexBlueprint
        instance = OmniplexBlueprint("test_omniplex")
        instance.debug = True
        instance._config = mock_config
        # Patch _get_model_instance to return a MagicMock
        instance._get_model_instance = MagicMock(return_value=MagicMock())
        # Patch mcp_server_configs as expected by agent creation logic
        instance.mcp_server_configs = mock_config['mcpServers']
        return instance

# --- Test Cases ---

import os
import pytest

skip_unless_test_llm = pytest.mark.skipif(os.environ.get("DEFAULT_LLM", "") != "test", reason="Only run if DEFAULT_LLM is not set to 'test'")

def test_omniplex_agent_creation_all_types(omniplex_blueprint_instance):
    """Test agent creation when all MCP server types are present."""
    blueprint = omniplex_blueprint_instance
    # Create mocks and set .name attribute directly
    m1 = MagicMock()
    m1.name = "npx_server_1"
    m2 = MagicMock()
    m2.name = "npx_server_2"
    m3 = MagicMock()
    m3.name = "uvx_server_1"
    m4 = MagicMock()
    m4.name = "other_server"
    m5 = MagicMock()
    m5.name = "memory"
    mock_mcps = [m1, m2, m3, m4, m5]
    starting_agent = blueprint.create_starting_agent(mcp_servers=mock_mcps)
    assert starting_agent is not None
    assert starting_agent.name == "OmniplexCoordinator"
    tool_names = {t.name for t in starting_agent.tools}
    assert "Amazo" in tool_names
    assert "Rogue" in tool_names
    assert "Sylar" in tool_names

def test_omniplex_agent_creation_only_npx(omniplex_blueprint_instance):
    """Test agent creation when only npx servers are present."""
    blueprint = omniplex_blueprint_instance
    blueprint.mcp_server_configs = {'npx_srv': {'command': 'npx ...'}} # Override config for test
    m1 = MagicMock()
    m1.name = "npx_srv"
    mock_mcps = [m1]
    starting_agent = blueprint.create_starting_agent(mcp_servers=mock_mcps)
    assert starting_agent.name == "OmniplexCoordinator"
    tool_names = {t.name for t in starting_agent.tools}
    assert "Amazo" in tool_names
    assert "Rogue" not in tool_names
    assert "Sylar" not in tool_names

@skip_unless_test_llm(reason="Blueprint interaction tests not yet implemented")
@pytest.mark.asyncio
async def test_omniplex_delegation_to_amazo(omniplex_blueprint_instance):
    """Test if Coordinator correctly delegates an npx task to Amazo."""
    # Needs Runner mocking, potentially mocking MCP interactions within Amazo.
    assert False

@skip_unless_test_llm(reason="Blueprint CLI tests not yet implemented")
def test_omniplex_cli_execution():
    """Test running the blueprint via CLI."""
    # Needs subprocess testing or direct call to main with mocks.
    assert False
