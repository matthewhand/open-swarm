import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY
import json
import logging
import copy
from typing import Dict, Any # Added import

# Import the module containing BlueprintBase directly for easier patching/access
import swarm.extensions.blueprint.blueprint_base as blueprint_base_module
from swarm.extensions.blueprint.blueprint_base import BlueprintBase # Keep for isinstance checks etc.

# Use the actual library Agent for type hints if appropriate
from agents import Agent as LibraryAgent

# Define a testable subclass locally
class TestableBlueprint(BlueprintBase):
    @property
    def name(self) -> str: return "TestableBP"
    def description(self) -> str: return "Desc"
    def create_starting_agent(self, mcp_servers=None) -> LibraryAgent: return MagicMock(spec=LibraryAgent)
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]: return {"output": "Test Run Result"}

# Mock configs for tests
MOCK_BASE_CONFIG = {
    "llm": { "default": {"provider": "openai", "model": "gpt-mock", "api_key": "default_key"} },
    "settings": {"default_markdown_output": False},
    "agents": {}
}
MOCK_ENV_CONFIG = {
    "llm": { "default": {"provider": "openai", "model": "gpt-mock", "api_key": "default_key"},
             "env_test": {"provider": "openai", "model": "env_model", "api_key": "${TEST_API_KEY}"} },
    "settings": {"default_markdown_output": False}, "agents": {}
}

class TestBlueprintBaseConfigLoading:

    @pytest.fixture(autouse=True)
    def setup_mocks(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "env_key_value")
        # Patch Runner WHERE IT IS USED (inside blueprint_base module)
        with patch('swarm.extensions.blueprint.blueprint_base.LibraryRunner') as mock_runner:
            # No need to patch load_config if tests use config_override primarily
            yield {"mock_runner": mock_runner}

    def test_init_calls_config_loaders(self, setup_mocks):
        """Verify __init__ processes config and instantiates Runner when using override."""
        test_config = copy.deepcopy(MOCK_BASE_CONFIG)
        # This instantiation should now call the patched LibraryRunner
        bp = TestableBlueprint(config_override=test_config)

        # Assert that the Runner (mock) was instantiated
        setup_mocks['mock_runner'].assert_called_once()
        # Assert config processing occurred
        assert bp.llm_profile == test_config['llm']['default']
        assert bp.markdown_output == test_config['settings']['default_markdown_output']

    # These tests don't strictly need setup_mocks anymore as they test config processing
    # which happens before Runner init, but keep it for consistency or if Runner needs config later.
    def test_get_llm_profile_success(self, setup_mocks, monkeypatch):
        """Test retrieving profile with env var sub (via config_override)."""
        test_config = copy.deepcopy(MOCK_ENV_CONFIG)
        bp = TestableBlueprint(profile="env_test", config_override=test_config)
        assert bp.llm_profile["api_key"] == "env_key_value"

    def test_get_llm_profile_missing_raises_error(self, setup_mocks):
        """Test ValueError if profile missing in config_override."""
        test_config_ok = copy.deepcopy(MOCK_BASE_CONFIG)
        with pytest.raises(ValueError, match="LLM profile 'non_existent' not found"):
            TestableBlueprint(profile="non_existent", config_override=test_config_ok)

        config_no_default = copy.deepcopy(MOCK_BASE_CONFIG); del config_no_default["llm"]["default"]
        with pytest.raises(ValueError, match="LLM profile 'default' not found"):
            TestableBlueprint(profile="default", config_override=config_no_default)

    def test_markdown_setting_priority(self, setup_mocks):
        """Test markdown setting priority with config_override."""
        test_config = copy.deepcopy(MOCK_BASE_CONFIG) # Config=False
        bp_cli_true = TestableBlueprint(markdown=True, config_override=test_config); assert bp_cli_true.markdown_output is True
        bp_cli_false = TestableBlueprint(markdown=False, config_override=test_config); assert bp_cli_false.markdown_output is False
        bp_config = TestableBlueprint(markdown=None, config_override=test_config); assert bp_config.markdown_output is False
        config_no_settings = copy.deepcopy(MOCK_BASE_CONFIG); del config_no_settings["settings"]
        bp_default = TestableBlueprint(markdown=None, config_override=config_no_settings); assert bp_default.markdown_output is True


# Test substitution logic separately - passed now
def test_substitute_env_vars_direct(monkeypatch):
    """Test the _substitute_env_vars helper directly."""
    substitute_func = BlueprintBase._substitute_env_vars
    monkeypatch.setenv("MY_VAR", "my_value")
    monkeypatch.setenv("ANOTHER", "another_value")
    monkeypatch.delenv("MISSING", raising=False)
    test_data = {"k1": "${MY_VAR}", "k2": ["$ANOTHER/path"], "k3": 1, "k4": "${MISSING}", "k5": "$HOME/path", "k6": "No vars here", "k7": "$MY_VAR${ANOTHER}", "k8": {}}
    expected = {"k1": "my_value", "k2": ["another_value/path"], "k3": 1, "k4": "${MISSING}", "k5": str(Path.home() / "path"), "k6": "No vars here", "k7": "my_valueanother_value", "k8": {}}
    result = substitute_func(test_data)
    assert result == expected

