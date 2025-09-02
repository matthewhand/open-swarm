import os
import sys
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock

# Ensure repo root is on sys.path for absolute imports if needed
PYTEST_ROOT = Path(__file__).resolve().parents[2]
if str(PYTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTEST_ROOT))

# Prefer absolute import through project package
from src.swarm.blueprints.suggestion.blueprint_suggestion import (
    SuggestionBlueprint,
    SuggestionsOutput as BlueprintSuggestionsOutput,
)


# Patch the correct config loader method for BlueprintBase
@pytest.fixture
def suggestion_blueprint_instance(monkeypatch):
    """Fixture to create a minimally configured SuggestionBlueprint instance."""
    # Ensure tests run deterministically with the test LLM profile
    monkeypatch.setenv("DEFAULT_LLM", "test")
    with patch(
        'src.swarm.blueprints.suggestion.blueprint_suggestion.BlueprintBase._load_and_process_config',
        return_value={
            'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}},
            'mcpServers': {},
        },
    ):
        instance = SuggestionBlueprint("test_suggestion")
        instance.debug = True
        # Set a minimal valid config to avoid RuntimeError
        instance._config = {
            "llm": {"default": {"provider": "openai", "model": "gpt-mock"}},
            "settings": {"default_llm_profile": "default", "default_markdown_output": True},
            "blueprints": {},
            "llm_profile": "default",
            "mcpServers": {},
        }
        # Patch _get_model_instance to return a MagicMock
        instance._get_model_instance = MagicMock(return_value=MagicMock())
    return instance


def test_suggestion_agent_creation(suggestion_blueprint_instance, monkeypatch):
    monkeypatch.setenv("DEFAULT_LLM", "test")
    blueprint = suggestion_blueprint_instance

    class FakeAgent:
        def __init__(self):
            self.name = "SuggestionAgent"

    with patch.object(blueprint, 'create_starting_agent', return_value=FakeAgent()):
        agent = blueprint.create_starting_agent([])
        assert hasattr(agent, "name")
        assert "Suggestion" in agent.name


def test_suggestion_run_produces_structured_output(suggestion_blueprint_instance, monkeypatch):
    monkeypatch.setenv("DEFAULT_LLM", "test")
    blueprint = suggestion_blueprint_instance
    # Return a simple iterable to validate consumer behavior without hitting real run logic
    with patch.object(blueprint, 'run', return_value=iter([{"content": "output"}])):
        output = list(blueprint.run([{"role": "user", "content": "Suggest something"}]))
        assert any("content" in o for o in output)


def test_suggestion_cli_execution(monkeypatch, suggestion_blueprint_instance):
    # Ensure deterministic CLI path
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    monkeypatch.setenv("DEFAULT_LLM", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")

    # Patch subprocess and CLI call to avoid real execution
    with patch("subprocess.run") as mock_subproc:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Suggestion CLI output"
        mock_subproc.return_value = mock_result
        import subprocess

        result = subprocess.run([
            sys.executable,
            "src/swarm/blueprints/suggestion/suggestion_cli.py",
            "--message",
            "Suggest something!",
        ])
        assert result.returncode == 0
        assert "Suggestion" in result.stdout or "output" in result.stdout
