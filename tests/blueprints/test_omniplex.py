import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call # Import call
from agents.mcp import MCPServer
from swarm.blueprints.omniplex.blueprint_omniplex import OmniplexBlueprint
import logging
import asyncio 

logger = logging.getLogger(__name__)

@pytest.fixture
def mock_mcp_servers():
    npx_server = MagicMock(spec=MCPServer); npx_server.name = "npx_server" 
    uvx_server = MagicMock(spec=MCPServer); uvx_server.name = "uvx_server"
    other_server = MagicMock(spec=MCPServer); other_server.name = "other_server"
    return [npx_server, uvx_server, other_server]

@pytest.fixture
def omniplex_blueprint_mocked_config(mock_mcp_servers):
    with patch('swarm.core.blueprint_base.BlueprintBase._load_configuration', return_value=None) as mock_load_config:
        with patch('swarm.blueprints.omniplex.blueprint_omniplex.OmniplexBlueprint._get_model_instance') as mock_get_model:
            mock_model_instance = MagicMock(name="MockModelInstance")
            mock_get_model.return_value = mock_model_instance
            
            blueprint = OmniplexBlueprint(blueprint_id="omniplex_test")
            
            mock_config_data = {
                'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock-omniplex'}},
                'mcpServers': { 
                    "npx_server": {"command": "npx some-tool", "type": "npx"},
                    "uvx_server": {"command": "uvx another-tool", "type": "uvx"},
                    "other_server": {"command": "python script.py", "type": "other"}
                },
                'settings': {'default_llm_profile': 'default'},
                'blueprints': {"omniplex_test": {}} 
            }
            blueprint._config = mock_config_data 
            if blueprint._config:
                 blueprint.mcp_server_configs = blueprint._config.get('mcpServers', {})
            else:
                 blueprint.mcp_server_configs = {}

            logger.debug(f"omniplex_fixture: Created blueprint instance {blueprint.blueprint_id} with mocked config.")
            yield blueprint

@pytest.mark.asyncio
async def test_omniplex_agent_creation_all_types(omniplex_blueprint_mocked_config, mock_mcp_servers):
    blueprint = omniplex_blueprint_mocked_config
    agent = blueprint.create_starting_agent(mock_mcp_servers) 
    assert agent is not None and agent.name == "OmniplexCoordinator"
    tool_names = {t.name for t in agent.tools}
    assert "Amazo" in tool_names and "Rogue" in tool_names and "Sylar" in tool_names

@pytest.mark.asyncio
async def test_omniplex_agent_creation_only_npx(omniplex_blueprint_mocked_config, mock_mcp_servers):
    blueprint = omniplex_blueprint_mocked_config
    npx_only_servers = [s for s in mock_mcp_servers if s.name == "npx_server"]
    agent = blueprint.create_starting_agent(npx_only_servers)
    assert agent is not None and agent.name == "OmniplexCoordinator"
    tool_names = {t.name for t in agent.tools}
    assert "Amazo" in tool_names and "Rogue" not in tool_names and "Sylar" not in tool_names

@pytest.mark.asyncio
async def test_omniplex_delegation_to_amazo(omniplex_blueprint_mocked_config, mock_mcp_servers):
    blueprint = omniplex_blueprint_mocked_config
    coordinator = blueprint.create_starting_agent(mock_mcp_servers)
    amazo_tool = next((t for t in coordinator.tools if t.name == "Amazo"), None)
    assert amazo_tool is not None
    if hasattr(amazo_tool, 'agent') and amazo_tool.agent:
        amazo_tool.agent.run = AsyncMock(return_value="Amazo processed npx task")

@pytest.mark.asyncio
async def test_omniplex_cli_execution(omniplex_blueprint_mocked_config, mock_mcp_servers):
    blueprint = omniplex_blueprint_mocked_config
    messages = [{"role": "user", "content": "Use npx_tool_1 to do something."}]

    # This function will replace agents.Runner.run
    # It must return an async generator instance when called.
    # We'll wrap it with a MagicMock to allow call assertions.
    
    async def actual_async_generator_func(*args_inner, **kwargs_inner):
        # args_inner will be (starting_agent, instruction)
        logger.debug(f"actual_async_generator_func called with args: {args_inner}, kwargs: {kwargs_inner}")
        yield {"messages": [{"role": "assistant", "content": f"Coordinator processed: {args_inner[1]}"}]}

    # Create a MagicMock that, when called, returns the result of calling our generator factory
    mock_runner_run_replacement = MagicMock(side_effect=lambda *a, **kw: actual_async_generator_func(*a, **kw))

    with patch('agents.Runner.run', new=mock_runner_run_replacement) as patched_runner_run:
        responses = []
        async for response in blueprint.run(messages, mcp_servers_override=mock_mcp_servers):
            logger.debug(f"Test received response: {response}")
            responses.append(response)
        
        assert len(responses) > 0, "No responses received from blueprint run"
        assert "Coordinator processed" in responses[0]["messages"][0]["content"]
        
        # Assert that our replacement was called
        patched_runner_run.assert_called_once()
        # Optionally, check arguments if needed:
        # starting_agent_arg = patched_runner_run.call_args[0][0]
        # instruction_arg = patched_runner_run.call_args[0][1]
        # assert instruction_arg == "Use npx_tool_1 to do something."
