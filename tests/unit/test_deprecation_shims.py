"""Verify former deprecation shims stay gone (use canonical swarm.core.* / swarm.ux.*).

Strangler-fig consolidation complete (see ROADMAP.md §2.1):
- swarm.core.spinner          (was swarm.blueprints.common.spinner, swarm.ux.spinner)
- swarm.core.config_loader    (was swarm.extensions.config.config_loader)
- swarm.ux.ansi_box           (was swarm.utils.ansi_box)
- swarm.core.swarm_api        (was swarm.extensions.launchers.swarm_api)
- swarm.extensions.blueprint  — deleted earlier
"""

import importlib
import warnings

import pytest

_GONE = (
    "swarm.blueprints.common.spinner",
    "swarm.ux.spinner",
    "swarm.extensions.config.config_loader",
    "swarm.utils.ansi_box",
    "swarm.extensions.launchers.swarm_api",
    "swarm.extensions.blueprint",
    "swarm.extensions.blueprint.spinner",
    "swarm.extensions.blueprint.slash_commands",
    "swarm.extensions.blueprint.blueprint_base",
    "swarm.extensions.blueprint.agent_utils",
    "swarm.extensions.blueprint.django_utils",
    "swarm.extensions.config.config_manager",
)


@pytest.mark.parametrize("module_name", _GONE)
def test_deprecated_shim_paths_stay_gone(module_name):
    with pytest.raises(ModuleNotFoundError):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            importlib.import_module(module_name)
