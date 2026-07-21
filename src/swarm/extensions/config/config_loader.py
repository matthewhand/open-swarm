# Thin delegate / reexport to central implementation in core (unification complete).
# All logic lives in swarm.core.config_loader to avoid duplication.
import warnings as _warnings
_warnings.warn(
    "swarm.extensions.config.config_loader is deprecated; use swarm.core.config_loader instead.",
    DeprecationWarning,
    stacklevel=2,
)
from swarm.core.config_loader import (  # noqa: F401,F403
    DEFAULT_CONFIG_FILENAME,
    _hint,
    _xdg_config_path,
    find_config_file,
    load_config,
    save_config,
    validate_config,
    get_profile_from_config,
    create_default_config,
    load_full_configuration,
    get_resolved_llm_profile,
    list_available_llm_profiles,
    _apply_litellm_overrides,
    _substitute_env_vars,
)

# For legacy direct use of resolve_placeholders etc. (some code still imports from here)
try:
    from swarm.core.config_manager import resolve_placeholders  # type: ignore
except Exception:
    resolve_placeholders = None  # type: ignore

import logging
logger = logging.getLogger(__name__)
logger.debug("extensions.config.config_loader now delegates to core (unified).")