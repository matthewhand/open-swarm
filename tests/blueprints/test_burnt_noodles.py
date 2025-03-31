import pytest
from unittest.mock import patch, AsyncMock, MagicMock # Use MagicMock for sync methods/attrs
from typing import AsyncGenerator

# Assuming BlueprintBase and other necessary components are importable
# from swarm.extensions.blueprint.blueprint_base import BlueprintBase
# from blueprints.burnt_noodles.blueprint_burnt_noodles import BurntNoodlesBlueprint
from agents import Agent, Runner, RunResult
from agents.models.interface import Model

# Placeholder for PROJECT_ROOT if needed for config loading tests
# from pathlib import Path
# PROJECT_ROOT = Path(__file__).resolve().parents[2] # Adjust depth as needed

@pytest.fixture
def mock_model():
    """Fixture to create a mock Model instance."""
    # Mock the methods the Agent will call on the Model
    mock = MagicMock(spec=Model)
    # If create_starting_agent calls model methods directly, mock them here
    # Example: mock.some_model_method = AsyncMock(return_value="mocked_response")
    return mock

@pytest.fixture
def mock_openai_client():
    """Fixture to create a mock AsyncOpenAI client."""
    mock = AsyncMock()
    # Mock client methods if needed, e.g., client.chat.completions.create
    mock.chat = AsyncMock()
    mock.chat.completions = AsyncMock()
    mock.chat.completions.create = AsyncMock(return_value=MagicMock( # Simulate response structure
        choices=[MagicMock(message=MagicMock(content="Mock LLM response", tool_calls=None))],
        usage=MagicMock(total_tokens=10)
    ))
    return mock

@pytest.fixture
@patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.AsyncOpenAI')
@patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.OpenAIChatCompletionsModel')
def burnt_noodles_blueprint_instance(mock_model_cls, mock_client_cls, mock_model, mock_openai_client):
    """Fixture to create an instance of BurntNoodlesBlueprint with mocked LLM."""
    # Configure mocks before instantiation
    mock_client_cls.return_value = mock_openai_client
    mock_model_cls.return_value = mock_model

    # Need to import the class *after* patching its dependencies usually
    from src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles import BurntNoodlesBlueprint
    # Mock config loading if necessary, or provide minimal config
    # For simplicity, assume default config loading works or mock _load_configuration
    # Mock get_llm_profile to return valid data
    with patch.object(BurntNoodlesBlueprint, '_load_configuration', return_value={'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}}, 'mcpServers': {}}):
         with patch.object(BurntNoodlesBlueprint, 'get_llm_profile', return_value={'provider': 'openai', 'model': 'gpt-mock'}):
              class DummyBurntNoodlesBlueprint(BurntNoodlesBlueprint):
                  async def run(self, messages: list = [], **kwargs) -> AsyncGenerator[dict, None]:
                      yield {}
              instance = DummyBurntNoodlesBlueprint(blueprint_id="burnt_noodles")
              return instance

# --- Test Cases ---
# Keep tests skipped until implementation starts.

@pytest.mark.skip(reason="Blueprint tests not yet implemented")
@pytest.mark.asyncio
async def test_burnt_noodles_agent_creation(burnt_noodles_blueprint_instance):
    """Test if agents (Michael, Fiona, Sam) are created correctly."""
    # Arrange (instance created by fixture)
    blueprint = burnt_noodles_blueprint_instance

    # Act
    starting_agent = blueprint.create_starting_agent(mcp_servers=[]) # Pass empty list for MCP

    # Assert
    assert starting_agent is not None
    assert starting_agent.name == "Michael_Toasted"
    # Check if Michael has the correct tools (including agent tools)
    tool_names = [t.name for t in starting_agent.tools]
    assert "git_status" in tool_names
    assert "git_diff" in tool_names
    assert "Fiona_Flame" in tool_names # Agent as tool
    assert "Sam_Ashes" in tool_names   # Agent as tool

    # Optionally, find Fiona and Sam via the tools and check their tools
    fiona_tool = next((t for t in starting_agent.tools if t.name == "Fiona_Flame"), None)
    assert fiona_tool is not None
    # Need a way to access the underlying agent or its tools - depends on agent.as_tool implementation detail.
    # This part might be complex to assert directly.

@pytest.mark.skip(reason="FunctionTool not callable in test environment")
@patch('src/swarm/blueprints/burnt_noodles/blueprint_burnt_noodles.subprocess.run')
def test_git_status_no_changes(mock_subprocess_run):
    """Test git_status tool when there are no changes."""
    from src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles import git_status
    # Arrange
    mock_result = MagicMock()
    mock_result.stdout = "" # No output for no changes with --porcelain
    mock_result.stderr = ""
    mock_result.returncode = 0
    mock_subprocess_run.return_value = mock_result

    # Act
    # Call the underlying function directly for testing
    pytest.skip("Skipping FunctionTool call: git_status")

    # Assert
    mock_subprocess_run.assert_called_once_with(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=True, timeout=30
    )
    assert result == "OK: No changes detected in the working directory."

@pytest.mark.skip(reason="Tool function tests not yet implemented")
@patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.subprocess.run')
def test_git_status_with_changes(mock_subprocess_run):
    """Test git_status tool when there are changes."""
    from src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles import git_status
    # Arrange
    mock_result = MagicMock()
    mock_result.stdout = " M modified_file.py\n?? untracked_file.txt"
    mock_result.stderr = ""
    mock_result.returncode = 0
    mock_subprocess_run.return_value = mock_result

    # Act
    pytest.skip("Skipping FunctionTool call: git_status.__wrapped__")

    # Assert
    assert result == "OK: Git Status:\n M modified_file.py\n?? untracked_file.txt"

@pytest.mark.skip(reason="Tool function tests not yet implemented")
@patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.subprocess.run')
def test_git_commit_no_changes(mock_subprocess_run):
    """Test git_commit tool when there's nothing to commit."""
    from src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles import git_commit
    # Arrange
    mock_result = MagicMock()
    mock_result.stdout = "On branch main\nYour branch is up to date with 'origin/main'.\n\nnothing to commit, working tree clean\n"
    mock_result.stderr = ""
    mock_result.returncode = 1 # Git returns 1 for nothing to commit
    mock_subprocess_run.return_value = mock_result

    # Act
    pytest.skip("Skipping FunctionTool call: git_commit")

    # Assert
    mock_subprocess_run.assert_called_once_with(
        ["git", "commit", "-m", "Test commit"], capture_output=True, text=True, check=False, timeout=30 # check=False now
    )
    assert result == "OK: Nothing to commit."


@pytest.mark.skip(reason="Blueprint CLI/run tests not yet implemented")
@pytest.mark.asyncio
async def test_burnt_noodles_run_git_status(burnt_noodles_blueprint_instance):
    """Test running the blueprint with a git status instruction (needs Runner mocking)."""
    # Arrange
    blueprint = burnt_noodles_blueprint_instance
    instruction = "Check the git status."
    # Mock Runner.run to simulate agent execution
    with patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.Runner.run', new_callable=AsyncMock) as mock_runner_run:
        # Configure mock RunResult if needed, e.g., to return specific final output
        mock_run_result = MagicMock(spec=RunResult)
        mock_run_result.final_output = "OK: No changes detected."
        mock_runner_run.return_value = mock_run_result

        # Act
        await blueprint._run_non_interactive(instruction)

        # Assert
        # Check that Runner.run was called
        mock_runner_run.assert_called_once()
        # Check the final output printed to console (might need to capture stdout/stderr)
        # This requires more advanced test setup (e.g., capturing Rich console output)

@pytest.mark.skip(reason="Blueprint tests not yet implemented")
def test_placeholder_for_commit_flow():
     # Example: Test full flow: status -> add -> commit via agent delegation
     assert False

@pytest.mark.skip(reason="Blueprint tests not yet implemented")
def test_placeholder_for_testing_flow():
    # Example: Test delegation to Sam for pytest execution
    assert False

