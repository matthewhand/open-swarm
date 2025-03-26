import json
import os
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock

# Import the modules we intend to patch
from swarm.extensions.blueprint import blueprint_discovery, blueprint_utils
from swarm.extensions.config import config_loader
from swarm import settings

# Patch targets AT THE POINT OF USE within the view module
DISCOVERY_TARGET = 'swarm.views.model_views.discover_blueprints' # Patched where view uses it
CONFIG_LOAD_TARGET = 'swarm.views.model_views.load_server_config' # Patched where view uses it
FILTER_TARGET = 'swarm.views.model_views.filter_blueprints' # Patched where view uses it
BLUEPRINTS_DIR_TARGET = 'swarm.views.model_views.BLUEPRINTS_DIR' # Patched where view uses it

class BlueprintFilterTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        if "SWARM_BLUEPRINTS" in os.environ: del os.environ["SWARM_BLUEPRINTS"]

        # Mock data remains the same
        self.mock_discovered_blueprints = { "echo": {"title": "Discovered Echo"}, "test_bp": {"title": "Test BP"}, "university": {"title": "Uni"} }
        self.mock_config_data = {
            "llm": {"mock_llm": {"passthrough": True}},
            "blueprints": {"echo": {"title": "Config Echo"}, "config_only": {"title": "Config Only"}}
        }

        # Start Patches - targeting the view module now
        self.patch_discover = patch(DISCOVERY_TARGET, return_value=self.mock_discovered_blueprints)
        self.mock_discover = self.patch_discover.start()

        # Patch load_server_config where the view uses it
        self.patch_load_config = patch(CONFIG_LOAD_TARGET, return_value=self.mock_config_data)
        self.mock_load_config = self.patch_load_config.start()

        # Patch filter_blueprints where the view uses it
        self.patch_filter = patch(FILTER_TARGET, side_effect=blueprint_utils.filter_blueprints) # Keep original logic via side_effect
        self.mock_filter = self.patch_filter.start()

        # Patch BLUEPRINTS_DIR where the view uses it
        self.patch_blueprints_dir = patch(BLUEPRINTS_DIR_TARGET, new='/dummy/blueprints/dir')
        self.patch_blueprints_dir.start()

    def tearDown(self):
        self.patch_blueprints_dir.stop()
        self.patch_filter.stop()
        self.patch_load_config.stop()
        self.patch_discover.stop()
        if "SWARM_BLUEPRINTS" in os.environ: del os.environ["SWARM_BLUEPRINTS"]

    def test_list_models_no_filter(self):
        """Test list_models when SWARM_BLUEPRINTS is not set."""
        url = reverse('list_models')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())

        # Check mocks are called
        self.mock_discover.assert_called_once()
        self.mock_load_config.assert_called_once()
        # The view *might* call filter even if env var is empty, check implementation
        # If filter handles empty string gracefully, it might be called.
        # If view checks env var first, it might not be called.
        # Let's assume the view calls filter, and filter handles empty allowed_str
        # self.mock_filter.assert_called_once() # Check if filter is called

        models_list = data.get("data", [])
        model_ids = {m["id"] for m in models_list}
        # Expect discovered + config + llms (config 'echo' overrides discovered 'echo')
        expected_ids = {"mock_llm", "echo", "config_only", "test_bp", "university"}
        self.assertEqual(model_ids, expected_ids)
        model_map = {m["id"]: m for m in models_list}
        self.assertEqual(model_map["echo"]["title"], "Config Echo") # Config overrides discovered


    def test_list_models_with_filter(self):
        """Test list_models when SWARM_BLUEPRINTS filters discovered blueprints."""
        os.environ["SWARM_BLUEPRINTS"] = "echo,university"

        url = reverse('list_models')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())

        self.mock_discover.assert_called_once()
        self.mock_load_config.assert_called_once()
        self.mock_filter.assert_called_once() # Filter should run

        # Check the arguments passed to the filter mock
        call_args, _ = self.mock_filter.call_args
        # Filter is called with the *result* of discover_blueprints
        self.assertEqual(call_args[0], self.mock_discovered_blueprints)
        # And the value from the environment variable
        self.assertEqual(call_args[1], "echo,university")

        models_list = data.get("data", [])
        model_ids = {m["id"] for m in models_list}
        # Expect LLM + config blueprints + *filtered* discovered blueprints
        expected_ids = {"mock_llm", "echo", "config_only", "university"} # test_bp is filtered out by SWARM_BLUEPRINTS
        self.assertEqual(model_ids, expected_ids)
        model_map = {m["id"]: m for m in models_list}
        self.assertEqual(model_map["echo"]["title"], "Config Echo") # Config overrides discovered
