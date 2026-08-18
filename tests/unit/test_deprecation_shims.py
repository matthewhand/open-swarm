"""Verify remaining deprecation shims and that removed paths stay gone.

Strangler-fig consolidation (see ROADMAP.md §2.1):
- swarm.core.spinner          <- swarm.blueprints.common.spinner, swarm.ux.spinner
- swarm.core.config_loader    <- swarm.extensions.config.config_loader
- swarm.ux.ansi_box           <- swarm.utils.ansi_box
- swarm.extensions.blueprint  — **deleted** (use swarm.core.*)
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


def test_extensions_blueprint_package_removed():
    """Former deprecation shim package must stay gone (use swarm.core.*)."""
    for gone in (
        "swarm.extensions.blueprint",
        "swarm.extensions.blueprint.spinner",
        "swarm.extensions.blueprint.slash_commands",
        "swarm.extensions.blueprint.blueprint_base",
        "swarm.extensions.blueprint.agent_utils",
        "swarm.extensions.blueprint.django_utils",
    ):
        with pytest.raises(ModuleNotFoundError):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                importlib.import_module(gone)


def test_removed_dead_modules_stay_gone():
    """Other import-broken internals must not resurface."""
    for dead in ("swarm.extensions.config.config_manager",):
        with pytest.raises(ModuleNotFoundError):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                importlib.import_module(dead)
