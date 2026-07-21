"""DEPRECATED shim: this module moved to ``swarm.core.config_loader``.

``swarm.core.config_loader`` is the single source of truth for configuration
loading/discovery. This module only re-exports it for backwards compatibility
and will be removed in a future release (see ROADMAP.md for the sunset plan).
"""

import warnings

from swarm.core.config_loader import (  # noqa: F401
    DEFAULT_CONFIG_FILENAME,
    _hint,
    _substitute_env_vars,
    _substitute_env_vars_recursive,
    _xdg_config_path,
    create_default_config,
    find_config_file,
    get_profile_from_config,
    load_config,
    load_environment,
    load_full_configuration,
    save_config,
    validate_config,
)

warnings.warn(
    "swarm.extensions.config.config_loader is deprecated; "
    "import from swarm.core.config_loader instead (see ROADMAP.md sunset notes).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "DEFAULT_CONFIG_FILENAME",
    "create_default_config",
    "find_config_file",
    "get_profile_from_config",
    "load_config",
    "load_environment",
    "load_full_configuration",
    "save_config",
    "validate_config",
]
