import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Assuming BlueprintBase and other necessary components are importable
# from blueprints.omniplex.blueprint_omniplex import OmniplexBlueprint
# from agents import Agent, Runner, RunResult, MCPServer

@pytest.fixture
def omniplex_blueprint_instance(tmp_path):
    """Fixture to create a mocked instance of OmniplexBlueprint."""
    # Mock config to define some servers with different command types
    mock_config = {
        'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}},
        'mcpServers': {
            'npx_server_1': {'command': 'npx something', 'args': []},
            'npx_server_2': {'command': ['/usr/bin/npx', 'another'], 'args': []},
            'uvx_server_1': {'command': ['uvx', 'run', 'tool'], 'args': []},
            'other_server': {'command': '/usr/local/bin/mytool', 'args': []},
            'memory': {'command': ['python', '-m', 'memory_server'], 'args': []} # Another 'other'
        }
    }
    # Mock get_llm_profile as well if _get_model_instance isn't fully mocked
    with patch('blueprints.omniplex.blueprint_omniplex.BlueprintBase._load_configuration', return_value=mock_config):
         with patch('blueprints.omniplex.blueprint_omniplex.BlueprintBase.get_llm_profile', return_value={'provider': 'openai', 'model': 'gpt-mock'}):
              with patch('blueprints.omniplex.blueprint_omniplex.BlueprintBase._get_model_instance') as mock_get_model:
                  mock_model_instance = MagicMock()
                  mock_get_model.return_value = mock_model_instance
                  from blueprints.omniplex.blueprint_omniplex import OmniplexBlueprint
                  # Pass the mocked config data for MCP server classification
                  instance = OmniplexBlueprint(debug=True)
                  instance.mcp_server_configs = mock_config['mcpServers'] # Ensure instance has access
    return instance

# --- Test Cases ---

@pytest.mark.skip(reason="Blueprint tests need refinement for dynamic MCPs")
def test_omniplex_agent_creation_all_types(omniplex_blueprint_instance):
    """Test agent creation when all MCP server types are present."""
    # Arrange
    blueprint = omniplex_blueprint_instance
    # Mock *started* MCP servers based on the mocked config
    mock_mcps = [
        MagicMock(spec=MCPServer, name="npx_server_1"),
        MagicMock(spec=MCPServer, name="npx_server_2"),
        MagicMock(spec=MCPServer, name="uvx_server_1"),
        MagicMock(spec=MCPServer, name="other_server"),
        MagicMock(spec=MCPServer, name="memory"),
    ]
    # Act
    starting_agent = blueprint.create_starting_agent(mcp_servers=mock_mcps)
    # Assert
    assert starting_agent is not None
    assert starting_agent.name == "OmniplexCoordinator"
    tool_names = {t.name for t in starting_agent.tools}
    assert "Amazo" in tool_names
    assert "Rogue" in tool_names
    assert "Sylar" in tool_names
    # We would need to inspect the tools/agents further to check their assigned MCPs

@pytest.mark.skip(reason="Blueprint tests need refinement for dynamic MCPs")
def test_omniplex_agent_creation_only_npx(omniplex_blueprint_instance):
    """Test agent creation when only npx servers are present."""
     # Arrange
    blueprint = omniplex_blueprint_instance
    blueprint.mcp_server_configs = {'npx_srv': {'command': 'npx ...'}} # Override config for test
    mock_mcps = [MagicMock(spec=MCPServer, name="npx_srv")]
    # Act
    starting_agent = blueprint.create_starting_agent(mcp_servers=mock_mcps)
    # Assert
    assert starting_agent.name == "OmniplexCoordinator"
    tool_names = {t.name for t in starting_agent.tools}
    assert "Amazo" in tool_names
    assert "Rogue" not in tool_names
    assert "Sylar" not in tool_names

@pytest.mark.skip(reason="Blueprint interaction tests not yet implemented")
@pytest.mark.asyncio
async def test_omniplex_delegation_to_amazo(omniplex_blueprint_instance):
    """Test if Coordinator correctly delegates an npx task to Amazo."""
    # Needs Runner mocking, potentially mocking MCP interactions within Amazo.
    assert False

@pytest.mark.skip(reason="Blueprint CLI tests not yet implemented")
def test_omniplex_cli_execution():
    """Test running the blueprint via CLI."""
    # Needs subprocess testing or direct call to main with mocks.
    assert False
