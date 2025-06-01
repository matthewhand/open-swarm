import pytest
from unittest.mock import patch, MagicMock, ANY
from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint
from rich.console import Console
import json 
import os 

@pytest.fixture
def geese_blueprint_instance(tmp_path):
    dummy_config_path = tmp_path / "dummy_geese_ux_config.json"
    dummy_config_content = {
        "llm": {"default": {"provider": "mock", "model": "mock-model-ux"}},
        "settings": {"default_llm_profile": "default", "default_markdown_output": True},
        "blueprints": {"test_geese_ux": {}} 
    }
    with open(dummy_config_path, "w") as f:
        json.dump(dummy_config_content, f)

    with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance') as mock_get_model:
        mock_model_instance = MagicMock(name="MockModelInstanceUX")
        mock_get_model.return_value = mock_model_instance
        
        instance = GeeseBlueprint(blueprint_id="test_geese_ux", config_path=str(dummy_config_path))
        instance.console = MagicMock(spec=Console) 
        return instance

def test_geese_spinner_states(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    assert hasattr(blueprint, 'update_spinner'), "Blueprint should have update_spinner method"
    assert blueprint.update_spinner("Quacking...", 0) == "Quacking..." 
    assert blueprint.update_spinner("Quacking...", 6.0) == "Quacking... Taking longer than expected"

def test_display_operation_box_basic(geese_blueprint_instance):
    blueprint = geese_blueprint_instance 
    blueprint.ux_print_operation_box(title="Test Box", content="Hello World", emoji="✨")
    args, _ = blueprint.console.print.call_args
    printed_string = args[0]
    assert "Test Box" in printed_string
    assert "Hello World" in printed_string
    assert "✨" in printed_string

def test_display_operation_box_default_emoji(geese_blueprint_instance):
    blueprint = geese_blueprint_instance
    blueprint.ux_print_operation_box(title="Default Test", content="Content here")
    args, _ = blueprint.console.print.call_args
    printed_string = args[0]
    assert "Default Test" in printed_string
    assert "🦆" in printed_string # Default emoji for "silly" style

@pytest.mark.asyncio
async def test_progressive_demo_operation_box(geese_blueprint_instance, monkeypatch):
    blueprint = geese_blueprint_instance
    monkeypatch.setenv("SWARM_TEST_MODE", "1") 

    blueprint.ux_print_operation_box = MagicMock() 
    
    results = []
    async for r in blueprint.run([{"role": "user", "content": "Test progressive demo"}]):
        results.append(r)
    
    assert blueprint.ux_print_operation_box.call_count == 0
    assert len(results) == 1
    assert results[0]["messages"][0]["content"] == "This is a creative response about teamwork."
