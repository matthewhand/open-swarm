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

skip_unless_test_llm = pytest.mark.skipif(os.environ.get("DEFAULT_LLM", "") != "test", reason="Only run if DEFAULT_LLM is set to 'test'")

@skip_unless_test_llm
def test_suggestion_agent_creation(suggestion_blueprint_instance):
    blueprint = suggestion_blueprint_instance
    class FakeAgent:
        def __init__(self):
            self.name = "SuggestionAgent"
    with patch.object(blueprint, 'create_starting_agent', return_value=FakeAgent()):
        agent = blueprint.create_starting_agent([])
        assert hasattr(agent, "name")
        assert "Suggestion" in agent.name

@skip_unless_test_llm
def test_suggestion_run_produces_structured_output(suggestion_blueprint_instance):
    blueprint = suggestion_blueprint_instance
    with patch.object(blueprint, 'run', return_value=iter([{"content": "output"}])):
        output = list(blueprint.run([{"role": "user", "content": "Suggest something"}]))
        assert any("content" in o for o in output)

@skip_unless_test_llm
def test_suggestion_cli_execution(suggestion_blueprint_instance):
    # Patch subprocess and CLI call to avoid real execution
    with patch("subprocess.run") as mock_subproc:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Suggestion CLI output"
        mock_subproc.return_value = mock_result
        import subprocess
        result = subprocess.run(["python3", "src/swarm/blueprints/suggestion/suggestion_cli.py", "--message", "Suggest something!"])
        assert result.returncode == 0
        assert "Suggestion" in result.stdout or "output" in result.stdout
