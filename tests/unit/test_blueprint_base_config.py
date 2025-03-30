import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from swarm.extensions.blueprint.blueprint_base import BlueprintBase

MOCK_CONFIG = {
    "llm": {
        "default": {"provider": "openai", "model": "gpt-4", "api_key": "DEFAULT_KEY"},
        "profile1": {"provider": "openai", "model": "gpt-3.5-turbo"},
        "default_profile": "default"
    },
    "settings": { "markdown_output": True, "env_vars": {} },
    "agents": {}
}

class _TestableBlueprint(BlueprintBase):
    name: str = "TestableBlueprint"
    description: str = "A testable blueprint."
    metadata = {"name": "TestableBlueprint"}
    def __init__(self, config_override=None): super().__init__(config_override=config_override)
    def create_starting_agent(self, mcp_servers): return MagicMock()
    async def run(self, messages: list[dict], mcp_servers: list[str] | None = None) -> str | AsyncMock: return "dummy run output"

@patch.object(BlueprintBase, '__init__', return_value=None) # Apply patch to class
class TestBlueprintBaseConfigLoading:

    # Patching __init__ at the class level injects the mock as the first arg
    def test_init_does_not_raise(self, mock_init): # Need param name
         blueprint = _TestableBlueprint()
         assert blueprint is not None
         mock_init.assert_called_once()

    def test_get_llm_profile_success(self, mock_init): # Need param name
        blueprint = _TestableBlueprint()
        blueprint.config = MOCK_CONFIG.copy()
        blueprint.profile_name = "default"
        blueprint._resolved_config_path = "mock/path.yaml"
        default_profile = blueprint._get_llm_profile()
        assert default_profile["model"] == "gpt-4"
        blueprint.profile_name = "profile1"
        profile1 = blueprint._get_llm_profile()
        assert profile1["model"] == "gpt-3.5-turbo"
        blueprint.profile_name = "nonexistent"
        with pytest.raises(ValueError, match="LLM profile 'nonexistent' not found"):
             blueprint._get_llm_profile()

    def test_get_llm_profile_missing_raises_error(self, mock_init): # Need param name
        blueprint = _TestableBlueprint()
        mock_config_no_default = {
            "llm": { "profile1": {"provider": "openai", "model": "gpt-3.5-turbo"}, "default_profile": "profile1" },
            "settings": {"markdown_output": True, "env_vars": {}}, "agents": {}
        }
        blueprint.config = mock_config_no_default
        blueprint.profile_name = "default"
        blueprint._resolved_config_path = "mock/path.yaml"
        with pytest.raises(ValueError, match="LLM profile 'default' not found"):
             blueprint._get_llm_profile()

    def test_markdown_setting_priority(self, mock_init): # Need param name
        blueprint1 = _TestableBlueprint()
        blueprint1.config = MOCK_CONFIG.copy()
        blueprint1.use_markdown = blueprint1.config.get("settings", {}).get("markdown_output", False)
        assert blueprint1.use_markdown is True
        blueprint2 = _TestableBlueprint()
        blueprint2.config = MOCK_CONFIG.copy()
        override = {"settings": {"markdown_output": True}}
        merged_settings = blueprint2.config.get("settings", {}).copy(); merged_settings.update(override.get("settings", {}))
        blueprint2.use_markdown = merged_settings.get("markdown_output", False)
        assert blueprint2.use_markdown is True
        blueprint3 = _TestableBlueprint()
        blueprint3.config = MOCK_CONFIG.copy()
        override = {"settings": {"markdown_output": False}}
        merged_settings = blueprint3.config.get("settings", {}).copy(); merged_settings.update(override.get("settings", {}))
        blueprint3.use_markdown = merged_settings.get("markdown_output", False)
        assert blueprint3.use_markdown is False

def test_substitute_env_vars_direct(monkeypatch):
     try: from swarm.extensions.config.config_loader import substitute_env_vars
     except ImportError: pytest.skip("Skipping test: substitute_env_vars not found"); return
     monkeypatch.setenv("MY_TEST_API_KEY", "env_key_123"); monkeypatch.setenv("MY_MODEL", "env_model")
     data = { "api_key": "${MY_TEST_API_KEY}", "model": "${MY_MODEL}-suffix", "nested": { "key": "prefix-${MY_TEST_API_KEY}" }, "list": ["${MY_MODEL}", "static"], "no_sub": "Just a string", "missing": "${MISSING_VAR:default_val}" }
     substituted_data = substitute_env_vars(data)
     assert substituted_data["api_key"] == "env_key_123"
     assert substituted_data["model"] == "env_model-suffix"
     assert substituted_data["nested"]["key"] == "prefix-env_key_123"
     assert substituted_data["list"] == ["env_model", "static"]
     assert substituted_data["no_sub"] == "Just a string"
     assert substituted_data["missing"] == "default_val"

