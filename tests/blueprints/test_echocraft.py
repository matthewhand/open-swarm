import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Assuming BlueprintBase and other necessary components are importable
# from blueprints.echocraft.blueprint_echocraft import EchoCraftBlueprint
# from agents import Agent, Runner, RunResult

@pytest.fixture
def echocraft_blueprint_instance():
    """Fixture to create a mocked instance of EchoCraftBlueprint."""
    # Mock config loading and model instantiation as it's simple
    with patch('blueprints.echocraft.blueprint_echocraft.BlueprintBase._load_configuration', return_value={'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}}, 'mcpServers': {}}):
         with patch('blueprints.echocraft.blueprint_echocraft.BlueprintBase._get_model_instance') as mock_get_model:
             mock_model_instance = MagicMock() # Simple mock, won't be used by EchoAgent logic
             mock_get_model.return_value = mock_model_instance
             # Import *after* patching
             from blueprints.echocraft.blueprint_echocraft import EchoCraftBlueprint
             instance = EchoCraftBlueprint(debug=True)
    return instance

# --- Test Cases ---

def test_echocraft_metadata(echocraft_blueprint_instance):
    """Test if the metadata is correctly defined."""
    # Arrange
    blueprint = echocraft_blueprint_instance
    # Assert
    assert blueprint.metadata["name"] == "EchoCraftBlueprint"
    assert blueprint.metadata["title"] == "EchoCraft"
    assert blueprint.metadata["version"] == "1.1.0"
    assert len(blueprint.metadata["required_mcp_servers"]) == 0

@pytest.mark.asyncio
async def test_echocraft_agent_creation(echocraft_blueprint_instance):
    """Test if the EchoAgent is created correctly."""
    # Arrange
    blueprint = echocraft_blueprint_instance
    # Act
    starting_agent = blueprint.create_starting_agent(mcp_servers=[])
    # Assert
    assert starting_agent is not None
    assert starting_agent.name == "Echo"
    assert len(starting_agent.tools) == 0
    # Check if it has the overridden process method
    assert hasattr(starting_agent, 'process')
    # Verify it's the custom EchoAgent class defined inside create_starting_agent
    assert "EchoAgent" in str(type(starting_agent))


@pytest.mark.asyncio
async def test_echocraft_run_echoes_input(echocraft_blueprint_instance):
    """Test if running the blueprint actually echoes the input."""
    # Arrange
    blueprint = echocraft_blueprint_instance
    instruction = "Hello, Echo!"

    # Mock the Runner.run to simulate the flow and check EchoAgent's direct output
    # Since EchoAgent overrides process, Runner might not call the LLM etc.
    # We can directly test the EchoAgent's process method here for simplicity,
    # or mock Runner.run to return the expected output. Let's test process directly.

    starting_agent = blueprint.create_starting_agent(mcp_servers=[])
    # Act
    result = await starting_agent.process(input_data=instruction)
    # Assert
    assert result == instruction

@pytest.mark.skip(reason="CLI tests require more setup/mocking or direct call checks")
def test_echocraft_cli_execution():
    """Test running the blueprint via CLI (placeholder)."""
    # Needs subprocess testing or direct call to main with mocked Runner/Agent.
    assert False

