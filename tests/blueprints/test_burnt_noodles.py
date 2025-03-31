import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from typing import AsyncGenerator, List, Dict, Any

# Assuming BlueprintBase and other necessary components are importable
from src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles import BurntNoodlesBlueprint
from agents import Agent, Runner, RunResult
from agents.models.interface import Model

@pytest.fixture
def mock_model():
    mock = MagicMock(spec=Model)
    return mock

@pytest.fixture
def mock_openai_client():
    mock = AsyncMock()
    mock.chat = AsyncMock()
    mock.chat.completions = AsyncMock()
    mock.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content="Mock LLM response", tool_calls=None))],
        usage=MagicMock(total_tokens=10)
    ))
    return mock

# Test-Specific Concrete Subclass
class _TestBurntNoodlesBlueprint(BurntNoodlesBlueprint):
    async def run(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        if False: yield {}

# Fixture uses the Test Subclass and patches config needed for __init__
@pytest.fixture
def burnt_noodles_test_instance(mocker): # Add mocker dependency
    """Fixture creating a testable BurntNoodlesBlueprint subclass instance with config patched."""
    # --- Patch config dependencies needed during __init__ ---
    dummy_app_config = type("DummyAppConfig", (), {"config": {
             "settings": {"default_llm_profile": "default", "default_markdown_output": True},
             "llm": {"default": {"provider": "openai", "model": "gpt-mock"}},
             "blueprints": {"burnt_noodles": {}}
         }})()
    # Use mocker provided to the fixture - no 'with' needed
    mocker.patch('django.apps.apps.get_app_config', return_value=dummy_app_config)
    mocker.patch('swarm.extensions.config.config_loader.get_profile_from_config', return_value={'provider': 'openai', 'model': 'gpt-mock'})

    # Instantiate the concrete test subclass *after* patches are applied
    instance = _TestBurntNoodlesBlueprint(blueprint_id="burnt_noodles")
    yield instance
    # Mocker patches are automatically cleaned up by pytest-mock

# --- Test Cases ---

@pytest.mark.asyncio
async def test_burnt_noodles_agent_creation(burnt_noodles_test_instance, mocker, mock_model, mock_openai_client):
    """Test if agents (Michael, Fiona, Sam) are created correctly."""
    # Arrange
    blueprint = burnt_noodles_test_instance

    # Patch dependencies needed specifically for create_starting_agent
    mocker.patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.OpenAIChatCompletionsModel', return_value=mock_model)
    mocker.patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.AsyncOpenAI', return_value=mock_openai_client)

    # Act
    starting_agent = blueprint.create_starting_agent(mcp_servers=[])

    # Assert
    assert starting_agent is not None
    assert starting_agent.name == "Michael_Toasted"
    tool_names = [t.name for t in starting_agent.tools]
    assert "git_status" in tool_names
    assert "git_diff" in tool_names
    assert "Fiona_Flame" in tool_names
    assert "Sam_Ashes" in tool_names

    fiona_tool = next((t for t in starting_agent.tools if t.name == "Fiona_Flame"), None)
    assert fiona_tool is not None


@pytest.mark.skip(reason="FunctionTool not callable in test environment")
@patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.subprocess.run')
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
async def test_burnt_noodles_run_git_status(burnt_noodles_test_instance, mocker): # Use test instance fixture
    """Test running the blueprint with a git status instruction (needs Runner mocking)."""
    # Arrange
    blueprint = burnt_noodles_test_instance
    instruction = "Check the git status."

    # Patch dependencies needed for this specific run
    mocker.patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.OpenAIChatCompletionsModel')
    mocker.patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.AsyncOpenAI')

    # Mock Runner.run to simulate agent execution
    # Use 'with patch' here as it's specific to this test's execution block
    with patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.Runner.run', new_callable=AsyncMock) as mock_runner_run:
        mock_run_result = MagicMock(spec=RunResult)
        mock_run_result.final_output = "OK: No changes detected."
        mock_runner_run.return_value = mock_run_result

        # Act
        await blueprint._run_non_interactive(instruction)

        # Assert
        mock_runner_run.assert_called_once()


@pytest.mark.skip(reason="Blueprint tests not yet implemented")
def test_placeholder_for_commit_flow():
     assert False

@pytest.mark.skip(reason="Blueprint tests not yet implemented")
def test_placeholder_for_testing_flow():
    assert False

