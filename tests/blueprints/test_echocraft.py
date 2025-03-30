
# --- Content for tests/blueprints/test_echocraft.py ---
import pytest
from typing import List, Dict, Any
import asyncio
from unittest.mock import patch, MagicMock # Import mock tools

from swarm.blueprints.echocraft.blueprint_echocraft import EchoCraftBlueprint

# Helper to collect results from async generator
async def collect_results(agen):
    return [item async for item in agen]

# Fixture to provide a mock app_config with a basic config dict
@pytest.fixture
def mock_app_config(mocker):
    mock_instance = MagicMock()
    mock_instance.config = {
        "llm": {"default": {"provider": "mock", "model": "mock-model"}},
        "settings": {"default_markdown_output": True, "default_llm_profile": "default"},
        "blueprints": {}
    }
    mocker.patch('django.apps.apps.get_app_config', return_value=mock_instance)
    return mock_instance

@pytest.mark.asyncio
async def test_echocraft_blueprint_run(mock_app_config): # Use the fixture
    """Tests the basic run functionality of EchoCraftBlueprint."""
    blueprint = EchoCraftBlueprint(blueprint_id="test_echo_run")
    messages = [{"role": "user", "content": "Hello"}]
    expected_output = "Echo: Hello"

    results = await collect_results(blueprint.run(messages))

    assert len(results) > 0
    final_message = results[-1]
    assert "id" in final_message
    assert "object" in final_message
    assert final_message["object"] == "chat.completion"
    assert "choices" in final_message
    assert len(final_message["choices"]) == 1
    assert "message" in final_message["choices"][0]
    assert final_message["choices"][0]["message"]["role"] == "assistant"
    assert final_message["choices"][0]["message"]["content"] == expected_output

@pytest.mark.asyncio
async def test_echocraft_blueprint_no_user_message(mock_app_config): # Use the fixture
    """Tests that EchoCraft handles cases with no user message gracefully."""
    blueprint = EchoCraftBlueprint(blueprint_id="test_echo_nouser")
    messages = [{"role": "system", "content": "You are an echo bot."}]
    # --- CORRECTED expected_output ---
    expected_output = "Echo: No user message found."

    results = await collect_results(blueprint.run(messages))

    assert len(results) > 0
    final_message = results[-1]
    assert final_message["choices"][0]["message"]["content"] == expected_output

@pytest.mark.asyncio
async def test_echocraft_blueprint_multiple_messages(mock_app_config): # Use the fixture
    """Tests that EchoCraft uses the *last* user message."""
    blueprint = EchoCraftBlueprint(blueprint_id="test_echo_multi")
    messages = [
        {"role": "user", "content": "First"},
        {"role": "assistant", "content": "Ignore me"},
        {"role": "user", "content": "Second"},
    ]
    expected_output = "Echo: Second"

    results = await collect_results(blueprint.run(messages))

    assert len(results) > 0
    final_message = results[-1]
    assert final_message["choices"][0]["message"]["content"] == expected_output

