import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY
import os
from django.apps import apps # Import apps registry

# Assuming BlueprintBase is correctly importable now
from swarm.core.blueprint_base import BlueprintBase

# A minimal concrete implementation for testing
class _TestableBlueprint(BlueprintBase):
    def __init__(self, blueprint_id, config=None):
        super().__init__(blueprint_id, config=config)

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
            config = {
                "llm": {"default": {"provider": "mock"}},
                "settings": {"default_markdown_output": True, "default_llm_profile": "default"},
                "blueprints": {}
            }
            blueprint = _TestableBlueprint(blueprint_id="test_init", config=config)
            assert blueprint.blueprint_id == "test_init"
            assert blueprint.llm_profile_name == "default"
            assert blueprint.llm_profile["provider"] == "mock"
            assert blueprint.should_output_markdown is True
        except Exception as e:
            pytest.fail(f"BlueprintBase initialization failed: {e}")

    def test_markdown_setting_priority(self, mock_app_config_instance): # Use the fixture
        """Test markdown setting priority: blueprint > global."""
        # --- Test Case 1: Global True, Blueprint unspecified -> True ---
        config1 = {
            "llm": {"default": {"provider": "mock"}},
            "settings": {"default_markdown_output": True, "default_llm_profile": "default"},
            "blueprints": {}
        }
        blueprint1 = _TestableBlueprint(blueprint_id="bp1", config=config1)
        assert blueprint1.should_output_markdown is True, "Should default to global True"

        # --- Test Case 2: Global False, Blueprint unspecified -> False ---
        config2 = {
            "llm": {"default": {"provider": "mock"}},
            "settings": {"default_markdown_output": False, "default_llm_profile": "default"},
            "blueprints": {}
        }
        blueprint2 = _TestableBlueprint(blueprint_id="bp2", config=config2)
        assert blueprint2.should_output_markdown is False, "Should default to global False"

        # --- Test Case 3: Blueprint overrides global (True) ---
        config3 = {
            "llm": {"default": {"provider": "mock"}},
            "settings": {"default_markdown_output": False, "default_llm_profile": "default"},
            "blueprints": {"bp3": {"output_markdown": True}}
        }
        blueprint3 = _TestableBlueprint(blueprint_id="bp3", config=config3)
        assert blueprint3.should_output_markdown is True, "Blueprint setting (True) should override global (False)"

        # --- Test Case 4: Blueprint overrides global (False) ---
        config4 = {
            "llm": {"default": {"provider": "mock"}},
            "settings": {"default_markdown_output": True, "default_llm_profile": "default"},
            "blueprints": {"bp4": {"output_markdown": False}}
        }
        blueprint4 = _TestableBlueprint(blueprint_id="bp4", config=config4)
        assert blueprint4.should_output_markdown is False, "Blueprint setting (False) should override global (True)"
