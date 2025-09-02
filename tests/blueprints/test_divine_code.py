import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import importlib
import os
import sys
import types
import inspect # For isasyncgenfunction

# Patch import to point to zeus
sys.modules['swarm.blueprints.divine_code'] = importlib.import_module('swarm.blueprints.zeus')
sys.modules['swarm.blueprints.divine_code.blueprint_divine_code'] = importlib.import_module('swarm.blueprints.zeus.blueprint_zeus')

from swarm.blueprints.zeus.blueprint_zeus import ZeusBlueprint, ZeusSpinner # Import ZeusSpinner for its FRAMES

@pytest.fixture
def zeus_blueprint_instance():
    mock_config = {
        'llm': {'default': {'provider': 'openai', 'model': 'gpt-mock'}},
        'mcpServers': {},
        'settings': {'default_llm_profile': 'default', 'default_markdown_output': False},
        'blueprints': {'test_zeus': {'debug_mode': True}} 
    }
    with patch('swarm.core.blueprint_base.BlueprintBase._load_configuration', return_value=mock_config):
        with patch('swarm.core.blueprint_base.BlueprintBase._get_model_instance') as mock_get_model:
            mock_model_instance = MagicMock()
            mock_get_model.return_value = mock_model_instance
            instance = ZeusBlueprint(blueprint_id="test_zeus", debug=True) 
            instance._config = mock_config 
            instance.mcp_server_configs = {} 
            return instance

def test_zeus_agent_creation(zeus_blueprint_instance):
    blueprint = zeus_blueprint_instance
    m1 = MagicMock(); m1.name = "memory"
    m2 = MagicMock(); m2.name = "filesystem"
    m3 = MagicMock(); m3.name = "mcp-shell"
    agent = blueprint.create_starting_agent(mcp_servers=[m1, m2, m3])
    assert agent.name == "Zeus"
    assert hasattr(agent, "tools")
    tool_names = set()
    for t in agent.tools:
        if hasattr(t, "name"):
            tool_names.add(t.name)
        elif isinstance(t, dict) and "tool_name" in t:
            tool_names.add(t["tool_name"])
    expected_tools = {"Odin", "Hermes", "Hephaestus", "Hecate", "Thoth", "Mnemosyne", "Chronos"}
    assert expected_tools.issubset(tool_names)

@pytest.mark.asyncio
async def test_zeus_run_method(zeus_blueprint_instance):
    messages = [{"role": "user", "content": "Hello Zeus!"}]
    with patch.object(zeus_blueprint_instance, "create_starting_agent") as mock_create:
        class DummyAgent:
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "Hi!"}]}
        mock_create.return_value = DummyAgent()
        
        responses = []
        async for resp in zeus_blueprint_instance.run(messages):
            responses.append(resp)
        
        assert len(responses) >= 2, f"Expected at least 2 responses (spinner + agent), got {len(responses)}. Responses: {responses}"
        
        initial_spinner_msg_content = responses[0]["messages"][0]["content"]
        # BlueprintUXImproved.spinner(0) should return one of the initial spinner frames
        # We can check against ZeusSpinner.FRAMES[0] or a more general check
        assert initial_spinner_msg_content in ZeusSpinner.FRAMES or "Generating" in initial_spinner_msg_content, \
               f"First response was not a recognized spinner message: '{initial_spinner_msg_content}'. Expected one of {ZeusSpinner.FRAMES} or containing 'Generating'."

        # Second response should be the raw agent output because debug=True for the blueprint instance
        agent_response_msg = responses[1]["messages"][0]["content"]
        assert agent_response_msg == "Hi!", f"Agent response mismatch. Expected 'Hi!', got '{agent_response_msg}'"

@pytest.mark.asyncio
async def test_zeus_delegation_to_odin(zeus_blueprint_instance):
    """Ensure Odin appears as a delegatable tool in the created agent."""
    blueprint = zeus_blueprint_instance
    agent = blueprint.create_starting_agent(mcp_servers=[])
    names = set()
    for t in getattr(agent, 'tools', []):
        if hasattr(t, 'name'):
            names.add(t.name)
        elif isinstance(t, dict) and 'tool_name' in t:
            names.add(t['tool_name'])
    assert 'Odin' in names, f"Expected 'Odin' tool in Zeus agent tools; got {names}"

def test_zeus_basic():
    bp = ZeusBlueprint(debug=False)
    response = bp.assist("Hello")
    assert "How can Zeus help you today? You said: Hello" in response

@pytest.mark.asyncio
async def test_zeus_full_flow_example(zeus_blueprint_instance):
    """End-to-end: run yields spinner first, then agent output (debug=True)."""
    messages = [{"role": "user", "content": "Plan a release"}]
    # Use a dummy agent to keep deterministic
    with patch.object(zeus_blueprint_instance, "create_starting_agent") as mock_create:
        class DummyAgent:
            async def run(self, messages, **kwargs):
                yield {"messages": [{"role": "assistant", "content": "Plan: 1) Scope 2) Cut notes"}]}
        mock_create.return_value = DummyAgent()

        outputs = []
        async for item in zeus_blueprint_instance.run(messages):
            outputs.append(item)

        assert len(outputs) >= 2
        first = outputs[0]["messages"][0]["content"]
        second = outputs[1]["messages"][0]["content"]
        assert any(frame in first for frame in ZeusSpinner.FRAMES) or "Generating" in first
        assert "Plan:" in second

@pytest.mark.skip(reason="Blueprint CLI tests not yet implemented")
def test_zeus_cli_execution():
    assert False
