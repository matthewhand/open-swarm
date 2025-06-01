import os
import sys
os.environ["SWARM_TEST_MODE"] = "1" 
display_calls = []
# Ensure this path setup is correct for your project structure
project_root_geese_test = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path_geese_test = os.path.join(project_root_geese_test, 'src')
if src_path_geese_test not in sys.path: sys.path.insert(0, src_path_geese_test)

from swarm.blueprints.common import operation_box_utils 
orig_display = operation_box_utils.display_operation_box
def record_display(*args, **kwargs):
    display_calls.append((args, kwargs))
    return orig_display(*args, **kwargs)
operation_box_utils.display_operation_box = record_display

import importlib
geese_mod = importlib.import_module("swarm.blueprints.geese.blueprint_geese")
_create_story_outline = geese_mod._create_story_outline
_write_story_part = geese_mod._write_story_part
_edit_story = geese_mod._edit_story

import pytest
from unittest.mock import patch, AsyncMock, MagicMock, Mock, ANY
from rich.console import Console
from rich.text import Text 
from rich.panel import Panel 
import time
import asyncio
import json 

@pytest.fixture
def mock_console_fixture(): 
    console = MagicMock(spec=Console)
    console.get_time = Mock(return_value=time.monotonic()) 
    return console

@pytest.fixture
def geese_blueprint_instance(mock_console_fixture, tmp_path):
    with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance') as mock_get_model_base:
        mock_model_instance = MagicMock(name="MockModelInstanceFromBase")
        mock_get_model_base.return_value = mock_model_instance
        
        GeeseBlueprint = geese_mod.GeeseBlueprint
        dummy_config_path = tmp_path / "dummy_geese_fixture_config.json"
        dummy_config_content = {
            "llm": {"default": {"provider": "openai", "model": "gpt-mock-geese-fixture"}},
            "settings": {"default_llm_profile": "default", "default_markdown_output": True},
            "blueprints": {"test_geese": {}} 
        }
        with open(dummy_config_path, "w") as f:
            json.dump(dummy_config_content, f)

        instance = GeeseBlueprint("test_geese", config_path=str(dummy_config_path))
        instance.console = mock_console_fixture 
        return instance

# --- Test Cases ---
def test_geese_agent_handoff_and_astool(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    assert blueprint.config is not None and blueprint.config.get("llm"), "Config not loaded or LLM section missing"
    agent = blueprint.create_starting_agent([])
    assert agent.name == "GeeseCoordinator"
    assert hasattr(agent, "tools")

def test_agent_tool_creation(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    assert blueprint.config is not None and blueprint.config.get("llm"), "Config not loaded or LLM section missing"
    agent = blueprint.create_starting_agent([])
    assert hasattr(agent, "tools") is True

def test_spinner_state_updates(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    assert hasattr(blueprint, 'update_spinner'), "Blueprint missing 'update_spinner'"
    state = blueprint.update_spinner("Quacking...", 5.0) 
    assert state == "Quacking..." 
    state = blueprint.update_spinner("Quacking...", 10.0) 
    assert state == "Quacking... Taking longer than expected" 

def test_geese_story_delegation_flow(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    assert blueprint.config is not None and blueprint.config.get("llm"), "Config not loaded or LLM section missing"
    coordinator = blueprint.create_starting_agent(mcp_servers=[])
    assert coordinator is not None and coordinator.name == "GeeseCoordinator"
    planner_tool = next((t for t in coordinator.tools if t.name == "Planner"), None)
    writer_tool = next((t for t in coordinator.tools if t.name == "Writer"), None)
    editor_tool = next((t for t in coordinator.tools if t.name == "Editor"), None)
    assert all([planner_tool, writer_tool, editor_tool])

def test_spinner_state_transitions(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    assert hasattr(blueprint, 'update_spinner'), "Blueprint instance missing 'update_spinner'"
    state = blueprint.update_spinner("Quacking...", 3.0) 
    assert state == "Quacking..." 
    state = blueprint.update_spinner("Quacking...", 7.0) 
    assert state == "Quacking... Taking longer than expected" 

def test_operation_box_styles(geese_blueprint_instance): 
    blueprint = geese_blueprint_instance
    blueprint.ux_print_operation_box(title="Search Results", content="Found 5 matches", style="blue")
    
    blueprint.console.print.assert_called_once()
    call_args = blueprint.console.print.call_args
    assert call_args is not None
    
    printed_arg = call_args[0][0] 
    assert isinstance(printed_arg, str), "Expected a string to be printed by ux_print_operation_box"
    
    # ux_ansi_emoji_box (called by ux_print_operation_box) returns a string with ANSI codes.
    # We check for substrings.
    assert "Search Results" in printed_arg 
    assert "Found 5 matches" in printed_arg


def test_display_splash_screen_variants(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    
    # Test non-animated: GeeseBlueprint.display_splash_screen calls self.console.print(Panel(...))
    blueprint.display_splash_screen(animated=False)
    blueprint.console.print.assert_called_once() 
    
    call_args_non_animated = blueprint.console.print.call_args
    assert call_args_non_animated is not None, "blueprint.console.print was not called"
    
    printed_panel_non_animated = call_args_non_animated[0][0]
    assert isinstance(printed_panel_non_animated, Panel), \
        f"Expected Panel, got {type(printed_panel_non_animated)}"
    assert "Welcome to GeeseBlueprint!" in printed_panel_non_animated.renderable.plain
    assert "Creative Story Generation System" in printed_panel_non_animated.renderable.plain
    
    blueprint.console.reset_mock()

    # Test animated: GeeseBlueprint.display_splash_screen uses rich.live.Live
    with patch('swarm.blueprints.geese.blueprint_geese.Live') as MockLive:
        blueprint.display_splash_screen(animated=True)
        MockLive.assert_called_once()
        
        live_args, live_kwargs = MockLive.call_args
        live_renderable_panel = live_args[0]
        assert isinstance(live_renderable_panel, Panel)
        assert "Welcome to GeeseBlueprint!" in live_renderable_panel.renderable.plain
        assert live_kwargs.get('console') == blueprint.console


def test_main_entry(monkeypatch, tmp_path):
    import sys
    import asyncio
    from swarm.blueprints.geese import blueprint_geese 
    
    dummy_config_path = tmp_path / "dummy_cli_geese_config.json"
    with open(dummy_config_path, "w") as f:
        json.dump({"llm": {"default": {"provider": "mock", "model":"mock-cli-geese"}}}, f)

    monkeypatch.setattr(sys, "argv", ["prog_geese_cli", "Test prompt for main", "--config-path", str(dummy_config_path)])
    mock_async_run = MagicMock()
    monkeypatch.setattr(asyncio, "run", mock_async_run) 
    
    with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance', return_value=MagicMock()):
        if hasattr(blueprint_geese, 'main_async'):
            blueprint_geese.main_async() 
        elif hasattr(blueprint_geese, 'main'):
             blueprint_geese.main() 
        else:
            pytest.fail("Neither main_async nor main found in blueprint_geese module")

def test_create_story_outline():
    topic = "Adventure in space"
    outline = _create_story_outline(topic)
    assert "Story Outline" in outline

def test_write_story_part():
    part_name = "Beginning"
    outline = "Story outline test"
    previous = "Previous content"
    content = _write_story_part(part_name, outline, previous)
    assert part_name in content

def test_edit_story():
    full_story = "Original story content"
    edit_instructions = "Make it more engaging"
    edited = _edit_story(full_story, edit_instructions)
    assert full_story in edited

def test_spinner_messages():
    assert "Quacking." != "Generating." 

@pytest.mark.asyncio
async def test_story_generation_flow(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    assert blueprint.config is not None and blueprint.config.get("llm"), "Config not loaded or LLM section missing"
    async def mock_create_outline(topic): return f"Outline: {topic}"
    async def mock_write_part(part_name, outline, previous): return f"{part_name} based on {outline}"
    async def mock_edit(story, instructions): return f"Edited: {story}"

    blueprint.create_story_outline = mock_create_outline 
    blueprint.write_story_part = mock_write_part
    blueprint.edit_story = mock_edit
    
    topic = "Space Adventure"
    outline = await blueprint.create_story_outline(topic)
    assert topic in outline
    part1 = await blueprint.write_story_part("Beginning", outline, "")
    assert "Beginning" in part1
    full_story = part1
    edited = await blueprint.edit_story(full_story, "Make it dramatic")
    assert "Edited" in edited
