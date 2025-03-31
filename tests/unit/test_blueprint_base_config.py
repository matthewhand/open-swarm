import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY
import os
from django.apps import apps # Import apps registry

# Assuming BlueprintBase is correctly importable now
from swarm.extensions.blueprint.blueprint_base import BlueprintBase

# A minimal concrete implementation for testing
class _TestableBlueprint(BlueprintBase):
    async def run(self, messages, **kwargs):
        # Minimal async generator implementation - must contain yield
        if False: # Never actually yields in this test context
            yield {}
        # Cannot use 'return <value>' in an async generator

# Fixture to mock the result of apps.get_app_config('swarm')
@pytest.fixture
def mock_app_config_instance(mocker):
    # Create a mock instance that mimics the AppConfig instance
    mock_instance = MagicMock()
    # Set the 'config' attribute on the mock instance
    mock_instance.config = {
        "llm": {
            "default": {"provider": "mock", "model": "mock-model"}
        },
        "settings": {
            "default_markdown_output": True,
            "default_llm_profile": "default"
        },
        "blueprints": {}
    }
    # Patch apps.get_app_config to return this mock instance
    mocker.patch('django.apps.apps.get_app_config', return_value=mock_instance)
    return mock_instance # Return the instance so tests can modify its .config


# Use the fixture in the test class
@pytest.mark.usefixtures("mock_app_config_instance")
class TestBlueprintBaseConfigLoading:

    def test_init_does_not_raise(self):
        """Test that basic initialization with mocked config works."""
        try:
            blueprint = _TestableBlueprint(blueprint_id="test_init")
            assert blueprint.blueprint_id == "test_init"
            assert blueprint.llm_profile_name == "default"
            assert blueprint.llm_profile["provider"] == "mock"
            assert blueprint.should_output_markdown is True
        except Exception as e:
            pytest.fail(f"BlueprintBase initialization failed: {e}")

    def test_markdown_setting_priority(self, mock_app_config_instance): # Use the fixture
        """Test markdown setting priority: blueprint > global."""

        # --- Test Case 1: Global True, Blueprint unspecified -> True ---
        mock_app_config_instance.config = { # Modify the config on the mock instance
            "llm": {"default": {"provider": "mock"}},
            "settings": {"default_markdown_output": True, "default_llm_profile": "default"},
            "blueprints": {}
        }
        blueprint1 = _TestableBlueprint(blueprint_id="bp1")
        assert blueprint1.should_output_markdown is True, "Should default to global True"

        # --- Test Case 2: Global False, Blueprint unspecified -> False ---
        mock_app_config_instance.config = {
            "llm": {"default": {"provider": "mock"}},
            "settings": {"default_markdown_output": False, "default_llm_profile": "default"},
            "blueprints": {}
        }
        blueprint2 = _TestableBlueprint(blueprint_id="bp2")
        assert blueprint2.should_output_markdown is False, "Should default to global False"

        # --- Test Case 3: Global True, Blueprint False -> False ---
        mock_app_config_instance.config = {
            "llm": {"default": {"provider": "mock"}},
            "settings": {"default_markdown_output": True, "default_llm_profile": "default"},
            "blueprints": {"bp3": {"markdown_output": False}}
        }
        blueprint3 = _TestableBlueprint(blueprint_id="bp3")
        assert blueprint3.should_output_markdown is False, "Blueprint setting (False) should override global (True)"

        # --- Test Case 4: Global False, Blueprint True -> True ---
        mock_app_config_instance.config = {
            "llm": {"default": {"provider": "mock"}},
            "settings": {"default_markdown_output": False, "default_llm_profile": "default"},
            "blueprints": {"bp4": {"markdown_output": True}}
        }
        blueprint4 = _TestableBlueprint(blueprint_id="bp4")
        assert blueprint4.should_output_markdown is True, "Blueprint setting (True) should override global (False)"

