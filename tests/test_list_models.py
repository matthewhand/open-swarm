import json
import os
from django.test import TestCase, Client
from django.urls import reverse
import swarm.extensions.blueprint as bp
from swarm import views

class BlueprintFilterTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        os.environ["SWARM_BLUEPRINTS"] = ""

        # Store original values
        self.original_discover = bp.discover_blueprints
        self.original_config = views.config
        self.original_blueprints_metadata = views.blueprints_metadata

        # Mock discover_blueprints to respect SWARM_BLUEPRINTS
        def mock_discover_blueprints(directories=None):
            all_blueprints = {
                "echo": {"title": "Echo Blueprint", "description": "Echoes input"},
                "test_bp": {"title": "Test Blueprint", "description": "Test BP"}
            }
            allowed = os.getenv("SWARM_BLUEPRINTS")
            if allowed and allowed.strip():
                allowed_set = set(allowed.split(","))
                return {k: v for k, v in all_blueprints.items() if k in allowed_set}
            return all_blueprints

        bp.discover_blueprints = mock_discover_blueprints

        # Mock config and filter blueprints based on SWARM_BLUEPRINTS
        all_config_blueprints = {
            "echo": {"path": "/mock/path/echo", "api": True},
            "test_bp": {"path": "/mock/path/test_bp"}
        }
        views.config = {
            "llm": {
                "mock_llm": {"provider": "test", "model": "mock", "passthrough": True},
                "other_llm": {"provider": "test", "model": "other", "passthrough": False}
            },
            "blueprints": all_config_blueprints
        }
        # Apply initial filter (empty SWARM_BLUEPRINTS)
        views.blueprints_metadata = mock_discover_blueprints(directories=["/mock/path"])

    def tearDown(self):
        bp.discover_blueprints = self.original_discover
        views.config = self.original_config
        views.blueprints_metadata = self.original_blueprints_metadata
        if "SWARM_BLUEPRINTS" in os.environ:
            del os.environ["SWARM_BLUEPRINTS"]

    def test_list_models_with_filter(self):
        os.environ["SWARM_BLUEPRINTS"] = "echo"
        # Reapply filter to config blueprints after setting SWARM_BLUEPRINTS
        allowed_set = set(os.environ["SWARM_BLUEPRINTS"].split(","))
        views.config["blueprints"] = {
            k: v for k, v in views.config["blueprints"].items() if k in allowed_set
        }
        url = reverse('list_models')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())

        blueprint_ids = {model["id"] for model in data["data"] if model["object"] == "blueprint"}
        llm_ids = {model["id"] for model in data["data"] if model["object"] == "llm"}

        self.assertEqual(blueprint_ids, {"echo"})
        self.assertEqual(llm_ids, {"mock_llm"})

if __name__ == "__main__":
    import unittest
    unittest.main()
