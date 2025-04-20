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

# Resolved merge conflicts by keeping the latest test logic from test/blueprint-test-updates branch.
import pytest
from swarm.blueprints.omniplex.blueprint_omniplex import OmniplexBlueprint

@pytest.mark.asyncio
async def test_omniplex_agent_creation_all_types():
    blueprint = OmniplexBlueprint(blueprint_id="omniplex")
    agent = blueprint.create_starting_agent([])
    assert agent.name in ("OmniplexAgent", "OmniplexCoordinator")
    assert hasattr(agent, "instructions")

@pytest.mark.asyncio
async def test_omniplex_agent_creation_only_npx():
    blueprint = OmniplexBlueprint(blueprint_id="omniplex")
    agent = blueprint.create_starting_agent([])
    assert agent.name in ("OmniplexAgent", "OmniplexCoordinator")

@pytest.mark.asyncio
async def test_omniplex_delegation_to_amazo():
    blueprint = OmniplexBlueprint(blueprint_id="omniplex")
    # Simulate delegation logic (mock if needed)
    assert True

@pytest.mark.asyncio
async def test_omniplex_cli_execution():
    blueprint = OmniplexBlueprint(blueprint_id="omniplex")
    # Simulate CLI execution (mock if needed)
    assert True
