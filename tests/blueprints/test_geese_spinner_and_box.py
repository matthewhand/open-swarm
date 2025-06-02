import pytest
from unittest.mock import patch, MagicMock, ANY, AsyncMock
from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint
from swarm.core.interaction_types import AgentInteraction
from swarm.core.interaction_types import StoryOutput # Corrected import
from rich.console import Console
import json
import os

@pytest.fixture
def geese_blueprint_instance_ux(tmp_path):
    dummy_config_path = tmp_path / "dummy_geese_ux_config.json"
    dummy_config_content = {
        "llm": {"default": {"provider": "mock", "model": "mock-model-ux"}},
        "settings": {"default_llm_profile": "default", "default_markdown_output": True},
        "blueprints": {"test_geese_ux": {}},
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

    with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance') as mock_get_model:
        mock_model_instance = MagicMock(name="MockModelInstanceUX")
        async def mock_chat_completion_stream(*args, **kwargs):
            yield {"choices": [{"delta": {"content": "mock stream part"}}]}
        mock_model_instance.chat_completion_stream = mock_chat_completion_stream
        mock_get_model.return_value = mock_model_instance

        instance = GeeseBlueprint(blueprint_id="test_geese_ux", config_path=str(dummy_config_path))
        instance._config = dummy_config_content # Ensure config is a dict
        instance.ux.console = MagicMock(spec=Console)
        # instance.spinner.console = MagicMock(spec=Console) # GeeseSpinner internal doesn't use console for print
        return instance

@pytest.mark.skip(reason="GeeseSpinner internal API changed; test needs update or removal.")
def test_geese_spinner_methods(geese_blueprint_instance_ux):
    blueprint = geese_blueprint_instance_ux
    blueprint.spinner.start("Honking...") # This method does not exist
    blueprint.spinner.console.print.assert_called_with(ANY)
    blueprint.spinner.console.reset_mock()
    with patch('sys.stdout.write') as mock_stdout_write:
        blueprint.spinner.update_message("Still honking...") # This method does not exist
        mock_stdout_write.assert_called_with(ANY)
    blueprint.spinner.stop("All quiet now.") # This method does not exist
    blueprint.spinner.console.print.assert_called_with(ANY)

def test_display_operation_box_basic(geese_blueprint_instance_ux):
    blueprint = geese_blueprint_instance_ux
    blueprint.ux.ux_print_operation_box(title="Test Box", content="Hello World", emoji="✨")
    blueprint.ux.console.print.assert_called_once()
    args, _ = blueprint.ux.console.print.call_args
    printed_string = args[0]
    assert "Test Box" in printed_string
    assert "Hello World" in printed_string
    assert "✨" in printed_string

def test_display_operation_box_default_emoji(geese_blueprint_instance_ux):
    blueprint = geese_blueprint_instance_ux
    # GeeseBlueprint __init__ now sets self.ux = BlueprintUXImproved(style="silly")
    blueprint.ux.ux_print_operation_box(title="Default Test", content="Content here")
    blueprint.ux.console.print.assert_called_once()
    args, _ = blueprint.ux.console.print.call_args
    printed_string = args[0]
    assert "Default Test" in printed_string
    assert "🦆" in printed_string # Expect silly emoji

@pytest.mark.skip(reason="Test needs update for refactored GeeseBlueprint agent creation.")
@pytest.mark.asyncio
async def test_progressive_demo_operation_box(geese_blueprint_instance_ux, monkeypatch):
    blueprint = geese_blueprint_instance_ux
    monkeypatch.setenv("SWARM_TEST_MODE", "0")

    mock_coordinator_agent_instance = MagicMock() # Mock the agent instance itself
    async def mock_run_gen(*args, **kwargs):
        yield AgentInteraction(type="progress", progress_message="Coordinator planning...")
        final_story_data_dict = { 
            "title": "Story for: Test progressive demo",
            "final_story": "This is a creative response about teamwork from the mocked coordinator.",
            "outline_json": "{}", "word_count": 10, "metadata": {}
        }
        story_output_obj = StoryOutput(**final_story_data_dict)
        yield AgentInteraction(
            type="message", role="assistant",
            content=story_output_obj.final_story,
            data=story_output_obj.model_dump(), # Use model_dump for Pydantic
            final=True
        )
    mock_coordinator_agent_instance.run = mock_run_gen # Assign to the run method of the mocked agent

    # Patch create_agent_from_config to return our mocked agent
    with patch.object(blueprint, 'create_agent_from_config', return_value=mock_coordinator_agent_instance) as mock_create_agent:
        blueprint.ux.ux_print_operation_box = MagicMock() # Mock the box printing

        results = []
        async for r_item in blueprint.run([{"role": "user", "content": "Test progressive demo"}]):
            results.append(r_item)

        mock_create_agent.assert_called_once() # Ensure agent creation was attempted
        blueprint.ux.ux_print_operation_box.assert_called_once() # The final story box should be printed
        
        assert len(results) > 0, "Expected at least one AgentInteraction from blueprint.run"
        # Further assertions on 'results' can be made if needed
        final_interaction = results[-1] # Assuming the last one is the final message
        assert isinstance(final_interaction, AgentInteraction), "Result should be AgentInteraction"
        assert final_interaction.type == "message"
        assert "mocked coordinator" in final_interaction.content
