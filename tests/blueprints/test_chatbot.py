# print("[DEBUG][test_chatbot.py] Test file imported successfully.")

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Assuming BlueprintBase and other necessary components are importable
# from blueprints.chatbot.blueprint_chatbot import ChatbotBlueprint
# from agents import Agent, Runner, RunResult

@pytest.fixture
def chatbot_blueprint_instance():
    """Fixture to create a mocked instance of ChatbotBlueprint."""
    import sys
    import types
    import asyncio
    from unittest.mock import MagicMock
    # Patch sys.modules so blueprint_chatbot can import dependencies
    fake_modules = {
        'agents': MagicMock(),
        'agents.runner': MagicMock(),
        'agents.mcp': MagicMock(),
        'agents.models.interface': MagicMock(),
        'agents.models.openai_chatcompletions': MagicMock(),
        'openai': MagicMock(),
    }
    # Patch Agent mock to always have an async run method
    class AgentMock(MagicMock):
        async def run(self, *args, **kwargs):
            pass
    with patch.dict(sys.modules, fake_modules):
        with patch('swarm.blueprints.chatbot.blueprint_chatbot.Agent', AgentMock):
            with patch('swarm.blueprints.chatbot.blueprint_chatbot.BlueprintBase._load_and_process_config', return_value=None):
                with patch('swarm.blueprints.chatbot.blueprint_chatbot.ChatbotBlueprint._get_model_instance') as mock_get_model:
                    mock_model_instance = MagicMock()
                    mock_get_model.return_value = mock_model_instance
                    from swarm.blueprints.chatbot.blueprint_chatbot import ChatbotBlueprint
                    # Patch a dummy async run method at the class level to satisfy ABC
                    async def dummy_run(self, messages, **kwargs):
                        yield {"messages": []}
                    ChatbotBlueprint.run = dummy_run
                    instance = ChatbotBlueprint(blueprint_id="test-chatbot")
                    # Patch: Set model in test config to DEFAULT_LLM if present
                    import os
                    model_name = os.environ.get("DEFAULT_LLM", "gpt-mock")
                    instance._config = {
                        "llm_profile": "default",
                        "llm": {"default": {"provider": "openai", "model": model_name}},
                        "settings": {"default_llm_profile": "default"},
                        "mcpServers": {}
                    }
    return instance

# --- Test Cases ---

import traceback

def test_chatbot_agent_creation(chatbot_blueprint_instance):
    """Test that the ChatbotBlueprint creates a valid agent instance."""
    try:
        blueprint = chatbot_blueprint_instance
        agent = blueprint.create_starting_agent(mcp_servers=[])
        assert agent is not None
        assert hasattr(agent, "run")
    except Exception as e:
        # print("[DEBUG][test_chatbot_agent_creation] Exception:", e)
        traceback.print_exc()
        raise

@pytest.mark.skip(reason="Blueprint interaction tests not yet implemented")
@pytest.mark.asyncio
async def test_chatbot_run_conversation(chatbot_blueprint_instance):
    """Test running the blueprint with a simple conversational input."""
    # Arrange
    blueprint = chatbot_blueprint_instance
    instruction = "Hello there!"
    # Mock Runner.run
    with patch('swarm.blueprints.chatbot.blueprint_chatbot.Runner.run', new_callable=AsyncMock) as mock_runner_run:
        mock_run_result = MagicMock(spec=RunResult)
        mock_run_result.final_output = "General Kenobi!" # Mocked response
        mock_runner_run.return_value = mock_run_result

        # Act
        await blueprint._run_non_interactive(instruction)

        # Assert
        mock_runner_run.assert_called_once()
        # Need to capture stdout/stderr or check console output mock

@pytest.mark.skip(reason="Blueprint CLI tests not yet implemented")
def test_chatbot_cli_execution():
    """Test running the blueprint via CLI."""
    assert False
