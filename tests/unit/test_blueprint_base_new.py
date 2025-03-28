import pytest
import argparse
from unittest.mock import patch, MagicMock
import sys
import os
from typing import Dict, Any # Import Dict and Any

# Assume src is added to path for imports
try:
    from swarm.extensions.blueprint.blueprint_base import BlueprintBase
    from agents import Agent
except ImportError:
    pytest.skip("Skipping BlueprintBase tests, failed to import dependencies.", allow_module_level=True)

# --- Minimal Concrete Blueprint for Testing ---
class MockAgent(Agent):
     def __init__(self, name="mock", **kwargs): super().__init__(name=name, instructions="test", **kwargs)

class DummyBlueprint(BlueprintBase):
    @property
    def metadata(self) -> Dict[str, Any]: return {"title": "Dummy Test Blueprint", "version": "0.1", "required_mcp_servers": [], "env_vars": []}
    def create_agents(self) -> Dict[str, Agent]: return {"DummyAgent": MockAgent()}

# --- Basic Tests ---
def test_blueprint_base_initialization():
    mock_args = argparse.Namespace(debug=False, profile=None, config_path="non_existent_config.json", markdown=None)
    with patch('swarm.extensions.blueprint.blueprint_base.load_swarm_config', return_value={}):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
             blueprint = DummyBlueprint(cli_args=mock_args, cli_config_override={})
             assert blueprint is not None; assert isinstance(blueprint.agents, dict)
             assert "DummyAgent" in blueprint.agents; assert blueprint.starting_agent_name == "DummyAgent"
             assert blueprint.use_markdown == BlueprintBase.DEFAULT_MARKDOWN_CLI
             assert blueprint.max_llm_calls == BlueprintBase.DEFAULT_MAX_LLM_CALLS
             assert "default" in blueprint.llm_profiles

def test_blueprint_base_metadata():
    mock_args = argparse.Namespace(debug=False, profile=None, config_path="dummy", markdown=None)
    with patch('swarm.extensions.blueprint.blueprint_base.load_swarm_config', return_value={}):
         with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
              blueprint = DummyBlueprint(cli_args=mock_args); metadata = blueprint.metadata
              assert isinstance(metadata, dict); assert metadata.get("title") == "Dummy Test Blueprint"

def test_blueprint_config_merging():
    mock_args = argparse.Namespace(debug=False, profile="cli_profile", config_path="dummy_path.json", markdown=False)
    cli_override_config = {"max_llm_calls": 50}
    swarm_config_data = { "blueprints": { "defaults": {"max_llm_calls": 10, "default_markdown_cli": True}, "DummyBlueprint": {"max_llm_calls": 20, "llm_profile": "bp_profile"} }, "llm": { "default": {"model": "model-default"}, "cli_profile": {"model": "model-cli"}, "bp_profile": {"model": "model-bp"} } }
    with patch('swarm.extensions.blueprint.blueprint_base.load_swarm_config', return_value=swarm_config_data):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            blueprint = DummyBlueprint(cli_args=mock_args, cli_config_override=cli_override_config)
            assert blueprint.max_llm_calls == 50
            assert blueprint.config.get("llm_profile") == "cli_profile"
            assert blueprint.use_markdown is False
