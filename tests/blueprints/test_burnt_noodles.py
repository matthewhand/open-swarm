import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from typing import AsyncGenerator, List, Dict, Any
import subprocess # Import subprocess for CalledProcessError

# Assuming BlueprintBase and other necessary components are importable
from src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles import BurntNoodlesBlueprint
# --- Import the undecorated LOGIC functions for potential future use ---
from src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles import (
    _git_status_logic,
    _git_diff_logic,
    _git_add_logic,
    _git_commit_logic,
    _git_push_logic,
    _run_npm_test_logic,
    _run_pytest_logic
)
# --- End Import ---
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

# Test-Specific Concrete Subclass (May not be needed if source class is concrete)
class _TestBurntNoodlesBlueprint(BurntNoodlesBlueprint):
    pass # Inherits the run method from the refactored source

# Fixture uses the Test Subclass and patches config needed for __init__
@pytest.fixture
def burnt_noodles_test_instance(mocker): # Add mocker dependency
    """Fixture creating a testable BurntNoodlesBlueprint subclass instance with config patched."""
    dummy_app_config = type("DummyAppConfig", (), {"config": {
             "settings": {"default_llm_profile": "default", "default_markdown_output": True},
             "llm": {"default": {"provider": "openai", "model": "gpt-mock"}},
             "blueprints": {"burnt_noodles": {}}
         }})()
    mocker.patch('django.apps.apps.get_app_config', return_value=dummy_app_config)
    mocker.patch('swarm.extensions.config.config_loader.get_profile_from_config', return_value={'provider': 'openai', 'model': 'gpt-mock'})

    # Instantiate the blueprint class (now concrete)
    instance = BurntNoodlesBlueprint(blueprint_id="burnt_noodles")
    yield instance

# --- Test Cases ---

@pytest.mark.asyncio
async def test_burnt_noodles_agent_creation(burnt_noodles_test_instance, mocker, mock_model, mock_openai_client):
    """Test if agents (Michael, Fiona, Sam) are created correctly."""
    blueprint = burnt_noodles_test_instance
    mocker.patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.OpenAIChatCompletionsModel', return_value=mock_model)
    mocker.patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.AsyncOpenAI', return_value=mock_openai_client)
    starting_agent = blueprint.create_starting_agent(mcp_servers=[])
    assert starting_agent is not None
    assert starting_agent.name == "Michael_Toasted"
    tool_names = [t.name for t in starting_agent.tools]
    # --- Check for the *actual* tool names assigned by the decorator (logic function names) ---
    assert "_git_status_logic" in tool_names
    assert "_git_diff_logic" in tool_names
    # --- End change ---
    assert "Fiona_Flame" in tool_names
    assert "Sam_Ashes" in tool_names
    fiona_tool = next((t for t in starting_agent.tools if t.name == "Fiona_Flame"), None)
    assert fiona_tool is not None


# --- Tool Function Tests (Skipped for now) ---

@pytest.mark.skip(reason="Tool logic testing needs different approach (decorator interaction)")
@patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.subprocess.run')
def test_git_status_no_changes(mock_subprocess_run):
    """Test _git_status_logic when there are no changes."""
    mock_result = MagicMock(); mock_result.stdout = ""; mock_result.stderr = ""; mock_result.returncode = 0
    mock_subprocess_run.return_value = mock_result
    result = _git_status_logic()
    mock_subprocess_run.assert_called_once_with(["git", "status", "--porcelain"], capture_output=True, text=True, check=True, timeout=30)
    assert result == "OK: No changes detected in the working directory."

@pytest.mark.skip(reason="Tool logic testing needs different approach (decorator interaction)")
@patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.subprocess.run')
def test_git_status_with_changes(mock_subprocess_run):
    """Test _git_status_logic when there are changes."""
    mock_result = MagicMock(); mock_result.stdout = " M modified_file.py\n?? untracked_file.txt"; mock_result.stderr = ""; mock_result.returncode = 0
    mock_subprocess_run.return_value = mock_result
    result = _git_status_logic()
    mock_subprocess_run.assert_called_once_with(["git", "status", "--porcelain"], capture_output=True, text=True, check=True, timeout=30)
    # More robust assertion
    assert result.startswith("OK: Git Status:\n")
    assert " M modified_file.py" in result
    assert "?? untracked_file.txt" in result

@pytest.mark.skip(reason="Tool logic testing needs different approach (decorator interaction)")
@patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.subprocess.run')
def test_git_commit_no_changes(mock_subprocess_run):
    """Test _git_commit_logic when there's nothing to commit."""
    commit_msg = "Test commit"
    mock_result = MagicMock(); mock_result.stdout = "nothing to commit"; mock_result.stderr = ""; mock_result.returncode = 0
    mock_subprocess_run.return_value = mock_result
    result = _git_commit_logic(message=commit_msg)
    mock_subprocess_run.assert_called_once_with(["git", "commit", "-m", commit_msg], capture_output=True, text=True, check=False, timeout=30)
    assert result == "OK: Nothing to commit."

# --- End Tool Function Tests ---


@pytest.mark.skip(reason="Blueprint run/interaction tests not yet implemented")
@pytest.mark.asyncio
async def test_burnt_noodles_run_git_status(burnt_noodles_test_instance, mocker):
    """Test running the blueprint with a git status instruction (needs Runner mocking)."""
    blueprint = burnt_noodles_test_instance
    instruction = "Check the git status."
    mocker.patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.OpenAIChatCompletionsModel')
    mocker.patch('src.swarm.blueprints.burnt_noodles.blueprint_burnt_noodles.AsyncOpenAI')
    mock_run_result = MagicMock(spec=RunResult); mock_run_result.final_output = "OK: No changes detected."
    mock_runner_run = mocker.patch('agents.Runner.run', new_callable=AsyncMock, return_value=mock_run_result)
    results = [chunk async for chunk in blueprint.run(messages=[{"role": "user", "content": instruction}])]
    mock_runner_run.assert_called_once()
    assert results[-1]['messages'][0]['content'] == "OK: No changes detected."


@pytest.mark.skip(reason="Blueprint tests not yet implemented")
def test_placeholder_for_commit_flow():
     assert False

@pytest.mark.skip(reason="Blueprint tests not yet implemented")
def test_placeholder_for_testing_flow():
    assert False

