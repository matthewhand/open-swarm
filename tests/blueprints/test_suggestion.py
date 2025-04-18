import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/swarm')))
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Dict, List, TypedDict

# Assuming BlueprintBase and other necessary components are importable
from blueprints.suggestion.blueprint_suggestion import SuggestionBlueprint, SuggestionsOutput as BlueprintSuggestionsOutput
# from agents import Agent, Runner, RunResult

# Patch the correct config loader method for BlueprintBase
@pytest.fixture
def suggestion_blueprint_instance():
    """Fixture to create a mocked instance of SuggestionBlueprint."""
    with patch('blueprints.suggestion.blueprint_suggestion.BlueprintBase._load_and_process_config', return_value={'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}}, 'mcpServers': {}}):
        from blueprints.suggestion.blueprint_suggestion import SuggestionBlueprint
        instance = SuggestionBlueprint("test_suggestion")
        instance.debug = True
        # Set a minimal valid config to avoid RuntimeError
        instance._config = {
            "llm": {"default": {"provider": "openai", "model": "gpt-mock"}},
            "settings": {"default_llm_profile": "default", "default_markdown_output": True},
            "blueprints": {},
            "llm_profile": "default",
            "mcpServers": {}
        }
        # Patch _get_model_instance to return a MagicMock
        instance._get_model_instance = MagicMock(return_value=MagicMock())
    return instance

# --- Test Cases ---

import os
import pytest

skip_unless_test_llm = pytest.mark.skipif(os.environ.get("DEFAULT_LLM", "") != "test", reason="Only run if DEFAULT_LLM is not set to 'test'")

def test_suggestion_agent_creation(suggestion_blueprint_instance):
    """Test if the SuggestionAgent is created correctly with output_type."""
    # Arrange
    blueprint = suggestion_blueprint_instance
    # Act
    starting_agent = blueprint.create_starting_agent(mcp_servers=[])
    # Assert
    assert starting_agent is not None
    assert starting_agent.name == "SuggestionAgent"
    assert starting_agent.output_type == BlueprintSuggestionsOutput

import os
import pytest

skip_unless_test_llm = pytest.mark.skipif(os.environ.get("DEFAULT_LLM", "") != "test", reason="Only run if DEFAULT_LLM is not set to 'test'")

@skip_unless_test_llm(reason="Blueprint interaction tests not yet implemented")
@pytest.mark.asyncio
async def test_suggestion_run_produces_structured_output(suggestion_blueprint_instance):
    """Test running the blueprint and check if output matches SuggestionsOutput structure."""
    # Arrange
    blueprint = suggestion_blueprint_instance
    instruction = "I'm interested in learning about large language models."
    # Mock Runner.run to return a dict matching the structure
    with patch('blueprints.suggestion.blueprint_suggestion.Runner.run', new_callable=AsyncMock) as mock_runner_run:
        mock_output = {"suggestions": ["What specifically about LLMs interests you?", "Have you worked with any LLMs before?", "Are you looking for technical details or applications?"]}
        mock_run_result = MagicMock(spec=RunResult)
        mock_run_result.final_output = mock_output # Runner should return the parsed dict
        mock_runner_run.return_value = mock_run_result

        # Act
        # This requires capturing stdout/stderr or mocking self.console.print
        # For now, just assert the mocked return type
        await blueprint._run_non_interactive(instruction)
        # Assertions would go here based on captured output or console mock calls
        # e.g., assert '"suggestions": [' in captured_stdout

import os
import pytest

skip_unless_test_llm = pytest.mark.skipif(os.environ.get("DEFAULT_LLM", "") != "test", reason="Only run if DEFAULT_LLM is not set to 'test'")

@skip_unless_test_llm(reason="Blueprint CLI tests not yet implemented")
def test_suggestion_cli_execution():
    """Test running the blueprint via CLI."""
    assert False
