import pytest
import logging
from django.apps import apps

logger = logging.getLogger(__name__)

# Keep imports below for syntax checking, but they won't run
import json
import tempfile
import os
from pathlib import Path
from django.conf import settings
from importlib import reload
from collections import OrderedDict

@pytest.mark.usefixtures("settings")
class TestBlueprintLoading:

    @pytest.fixture(autouse=True)
    def setup_test_env(self, settings, monkeypatch):
        # If dynamic INSTALLED_APPS modification is needed, document it here.
        pass

    def test_blueprint_loading(self, settings):
        # Attempt to load at least one blueprint app
        blueprint_apps = [app for app in apps.get_app_configs() if app.name.startswith('swarm.blueprints.')]
        assert blueprint_apps, (
            "No swarm.blueprints.* apps loaded. If this test fails, dynamic INSTALLED_APPS setup must be fixed "
            "so blueprints are discoverable during test runs. See ISSUES.md for guidance.")
        logger.info(f"Loaded blueprint apps: {[app.name for app in blueprint_apps]}")
