"""Verify deprecation shims re-export the canonical implementations.

Strangler-fig consolidation (see ROADMAP.md sunset notes):
- swarm.core.spinner          <- swarm.blueprints.common.spinner, swarm.ux.spinner,
                                 swarm.extensions.blueprint.spinner
- swarm.core.config_loader    <- swarm.extensions.config.config_loader
- swarm.ux.ansi_box           <- swarm.utils.ansi_box
- swarm.core (blueprint base) <- swarm.extensions.blueprint
"""

import importlib
import warnings

import pytest


def _import_with_deprecation(module_name):
    """Import (or reload) a module, asserting it emits DeprecationWarning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        module = importlib.import_module(module_name)
        module = importlib.reload(module)
    assert any(issubclass(w.category, DeprecationWarning) for w in caught), (
        f"{module_name} did not emit DeprecationWarning on import"
    )
    return module


def test_common_spinner_shim():
    shim = _import_with_deprecation("swarm.blueprints.common.spinner")
    from swarm.core.spinner import SwarmSpinner

    assert shim.SwarmSpinner is SwarmSpinner


def test_ux_spinner_shim():
    shim = _import_with_deprecation("swarm.ux.spinner")
    from swarm.core.spinner import Spinner

    assert shim.Spinner is Spinner


def test_extensions_blueprint_spinner_shim():
    shim = _import_with_deprecation("swarm.extensions.blueprint.spinner")
    from swarm.core.spinner import Spinner, SwarmSpinner

    assert shim.Spinner is Spinner
    assert shim.SwarmSpinner is SwarmSpinner


def test_extensions_blueprint_package_shim():
    pkg = _import_with_deprecation("swarm.extensions.blueprint")
    from swarm.core.blueprint_base import BlueprintBase
    from swarm.core.blueprint_discovery import discover_blueprints
    from swarm.core.blueprint_utils import filter_blueprints

    assert pkg.BlueprintBase is BlueprintBase
    assert pkg.discover_blueprints is discover_blueprints
    assert pkg.filter_blueprints is filter_blueprints


def test_extensions_blueprint_slash_commands_shim():
    shim = _import_with_deprecation("swarm.extensions.blueprint.slash_commands")
    from swarm.core.slash_commands import SlashCommandRegistry, slash_registry

    assert shim.SlashCommandRegistry is SlashCommandRegistry
    assert shim.slash_registry is slash_registry


def test_extensions_config_loader_shim():
    shim = _import_with_deprecation("swarm.extensions.config.config_loader")
    from swarm.core import config_loader as core_loader

    assert shim.load_config is core_loader.load_config
    assert shim.find_config_file is core_loader.find_config_file
    assert shim.create_default_config is core_loader.create_default_config
    assert shim.save_config is core_loader.save_config
    assert shim.validate_config is core_loader.validate_config
    assert shim.get_profile_from_config is core_loader.get_profile_from_config
    assert shim.load_full_configuration is core_loader.load_full_configuration
    assert shim.DEFAULT_CONFIG_FILENAME == core_loader.DEFAULT_CONFIG_FILENAME


def test_utils_ansi_box_shim():
    shim = _import_with_deprecation("swarm.utils.ansi_box")
    from swarm.ux.ansi_box import ansi_box

    assert shim.ansi_box is ansi_box


def test_removed_dead_modules_stay_gone():
    """The import-broken extensions.blueprint internals must not resurface."""
    for dead in (
        "swarm.extensions.blueprint.blueprint_base",
        "swarm.extensions.blueprint.agent_utils",
        "swarm.extensions.blueprint.django_utils",
        "swarm.extensions.config.config_manager",
    ):
        with pytest.raises(ModuleNotFoundError):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                importlib.import_module(dead)
