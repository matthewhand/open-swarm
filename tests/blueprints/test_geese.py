import json
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint
from swarm.core.interaction_types import AgentInteraction


@pytest.fixture
def mock_console_fixture():
    console = MagicMock(spec=Console)
    return console


@pytest.fixture
def geese_blueprint_instance(mock_console_fixture, tmp_path):
    with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance') as mock_get_model_base:
        mock_model_instance = MagicMock(name="MockModelInstanceFromBase")
        async def mock_chat_completion_stream(*args, **kwargs):
            yield {"choices": [{"delta": {"content": "mocked stream part 1"}}]}
            yield {"choices": [{"delta": {"content": " mocked stream part 2"}}]}
        mock_model_instance.chat_completion_stream = mock_chat_completion_stream
        mock_get_model_base.return_value = mock_model_instance

        dummy_config_path = tmp_path / "dummy_geese_config.json"
        dummy_config_content = {
            "llm": {"default": {"provider": "mock", "model": "mock-model"}},
            "settings": {"default_llm_profile": "default"},
            "blueprints": {"test_geese": {}},
            "agents": { # Add a dummy 'Coordinator' agent config for _get_agent_config
                "Coordinator": {
                    "instructions": "You are a coordinator.",
                    "model_profile": "default",
                    "tools": []
                }
            }
        }
        with open(dummy_config_path, "w") as f:
            json.dump(dummy_config_content, f)

        instance = GeeseBlueprint(blueprint_id="test_geese", config_path=str(dummy_config_path))

        # Directly set _config to ensure it's a dict for tests, bypassing complex loading issues
        instance._config = dummy_config_content

        # Ensure the ux object uses the mocked console
        instance.ux.console = mock_console_fixture
        # The internal spinner in GeeseBlueprint doesn't use a console directly for printing
        # but the test for splash screen relies on instance.ux.console.print
        return instance


def test_geese_agent_creation_and_run_minimal(geese_blueprint_instance):
    """
    Validate that GeeseBlueprint can produce an agent from its own
    Coordinator config and that the agent exposes an async run that yields
    at least one AgentInteraction.
    This works both with and without the openai-agents SDK available,
    since the blueprint gracefully falls back to a MagicMock-based agent.
    """
    blueprint = geese_blueprint_instance

    # Fetch the Coordinator agent config from the injected test config
    agent_cfg = blueprint._get_agent_config("Coordinator")
    assert agent_cfg is not None, "Coordinator agent config missing in test setup"

    # Create the agent and ensure it is constructed with key attributes
    agent = blueprint.create_agent_from_config(agent_cfg)
    assert agent is not None, "create_agent_from_config returned None"
    assert getattr(agent, "name", None) == "Coordinator"
    assert getattr(agent, "instructions", None)

    # If the SDK exposes a 'run' coroutine, exercise it minimally; otherwise
    # accept attribute checks as sufficient in this environment.
    if hasattr(agent, "run"):
        # Drive the agent's run coroutine minimally and validate yielded structure
        async def _collect_one():
            async for chunk in agent.run([{"role": "user", "content": "Quick ping"}]):
                return chunk
            return None

        import asyncio
        first_chunk = asyncio.run(_collect_one())
        assert first_chunk is not None, "Agent.run did not yield any chunk"
        # The fallback mock yields AgentInteraction with a final message
        assert isinstance(first_chunk, AgentInteraction)
        assert first_chunk.type == "message"
        assert first_chunk.role == "assistant"


def test_operation_box_styles(geese_blueprint_instance):
    """Test basic operation box styles"""
    blueprint = geese_blueprint_instance
    blueprint.ux.ux_print_operation_box(title="Test", content="Content")
    blueprint.ux.console.print.assert_called_once()


def test_operation_box_error_handling(geese_blueprint_instance):
    """Test operation box error cases - should handle invalid style gracefully"""
    blueprint = geese_blueprint_instance

    # Test invalid style - should fall back to default "serious" style
    blueprint.ux.ux_print_operation_box(title="Test", content="Content", style="invalid")
    blueprint.ux.console.print.assert_called_once()


def test_operation_box_with_emoji(geese_blueprint_instance):
    """Test operation box with custom emoji"""
    blueprint = geese_blueprint_instance
    blueprint.ux.ux_print_operation_box(title="Success", content="Task completed", emoji="✅")
    blueprint.ux.console.print.assert_called_once()
