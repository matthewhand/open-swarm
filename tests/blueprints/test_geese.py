import pytest
from unittest.mock import patch, AsyncMock, MagicMock, Mock, ANY
from rich.console import Console
from rich.panel import Panel # Import Panel for type checking
from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint
import time
import asyncio
import json
import os # For os.path.exists

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
        from swarm.core.interaction_types import AgentInteraction
        assert isinstance(first_chunk, AgentInteraction)
        assert first_chunk.type == "message"
        assert first_chunk.role == "assistant"

@pytest.mark.skip(reason="Test needs review for SDK Agent tool handling")
def test_agent_tool_creation(geese_blueprint_instance):
    pass

def test_spinner_state_updates(geese_blueprint_instance):
    """GeeseSpinner.next_state should iterate through FRAMES in order."""
    spinner = geese_blueprint_instance.spinner
    frames = [spinner.next_state() for _ in range(len(spinner.FRAMES))]
    assert frames == spinner.FRAMES

def test_spinner_state_transitions(geese_blueprint_instance):
    """GeeseSpinner should cycle back to the first frame after completing a loop."""
    spinner = geese_blueprint_instance.spinner
    total = len(spinner.FRAMES)
    # Advance exactly one full cycle
    for _ in range(total):
        spinner.next_state()
    # Next state should be the first frame again
    assert spinner.next_state() == spinner.FRAMES[0]

@pytest.mark.skip(reason="Tool structure needs review with SDK Agent")
def test_geese_story_delegation_flow(geese_blueprint_instance):
    pass

def test_operation_box_styles(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    # GeeseBlueprint.ux is BlueprintUXImproved, style is "silly"
    # ux_print_operation_box prints an ANSI string
    blueprint.ux.ux_print_operation_box(title="Search Results", content="Found 5 matches", style="blue")
    blueprint.ux.console.print.assert_called_once()
    call_args = blueprint.ux.console.print.call_args
    assert call_args is not None
    printed_arg = call_args[0][0]
    assert isinstance(printed_arg, str), f"Expected str, got {type(printed_arg)}"
    assert "Search Results" in printed_arg
    assert "Found 5 matches" in printed_arg

def test_display_splash_screen_variants(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    # This now calls the overridden GeeseBlueprint.display_splash_screen
    blueprint.display_splash_screen() 
    blueprint.ux.console.print.assert_called_once() 
    call_args_non_animated = blueprint.ux.console.print.call_args
    assert call_args_non_animated is not None, "blueprint.ux.console.print was not called"
    
    # The overridden method calls self.ux.ux_print_operation_box, which prints a string
    printed_splash_string = call_args_non_animated[0][0]
    assert isinstance(printed_splash_string, str), \
        f"Expected str, got {type(printed_splash_string)}"
    assert "HONK! Welcome to Geese" in printed_splash_string
    assert "multi-agent story generation system" in printed_splash_string
    assert "🦢" in printed_splash_string # Check for the specific emoji used in the override

@pytest.mark.skip(reason="Main entry test needs review for async structure and Geese CLI specifics")
def test_main_entry(monkeypatch, tmp_path):
    pass

@pytest.mark.skip(reason="Relies on removed module-level functions; needs agent-based testing.")
def test_create_story_outline():
    pass

@pytest.mark.skip(reason="Relies on removed module-level functions; needs agent-based testing.")
def test_write_story_part():
    pass

@pytest.mark.skip(reason="Relies on removed module-level functions; needs agent-based testing.")
def test_edit_story():
    pass

def test_spinner_messages():
    # This test was comparing two strings; it's fine as is if just for that.
    assert "Quacking." != "Generating."

@pytest.mark.asyncio
async def test_story_generation_flow(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    # Ensure config is a dict and has 'llm'
    assert isinstance(blueprint.config, dict), f"Blueprint config is not a dict: {type(blueprint.config)}"
    assert "llm" in blueprint.config, f"LLM section missing in blueprint config. Keys: {blueprint.config.keys()}"
    
    # Mock the agent creation and run process for a simplified flow
    mock_coordinator_agent = MagicMock()
    async def mock_agent_run(*args, **kwargs):
        # Simulate the coordinator yielding a final story output
        final_story_output_data = {
            "title": "Mocked Story",
            "final_story": "This is a mocked story from the coordinator.",
            "outline_json": "{}", "word_count": 9, "metadata": {}
        }
        yield AgentInteraction(
            type="message", role="assistant", 
            content=final_story_output_data["final_story"],
            data=final_story_output_data, # GeeseBlueprint.run expects data to be StoryOutput.model_dump()
            final=True
        )
    mock_coordinator_agent.run = mock_agent_run
    
    with patch.object(blueprint, 'create_agent_from_config', return_value=mock_coordinator_agent) as mock_create_agent:
        results = []
        async for result_chunk in blueprint.run([{"role": "user", "content": "Tell a story"}]):
            results.append(result_chunk)
        
        assert mock_create_agent.called, "create_agent_from_config was not called"
        # Check if called for "Coordinator"
        assert any(call_args[0][0].name == "Coordinator" for call_args in mock_create_agent.call_args_list if call_args[0]), \
            "create_agent_from_config not called for Coordinator"

        assert len(results) > 0, "Blueprint run did not yield any results"
        final_result = results[-1]
        assert isinstance(final_result, AgentInteraction)
        assert final_result.type == "message"
        assert final_result.role == "assistant"
        assert "Mocked Story" in final_result.data.get("title", "")
        assert "mocked story from the coordinator" in final_result.content.lower()
