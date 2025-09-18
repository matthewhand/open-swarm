"""
Blueprint Extension Package for Open Swarm.

Provides the base class, discovery mechanisms, and utilities for creating
and running autonomous agent workflows (blueprints).
"""

# Core components
from swarm.core.blueprint_base import BlueprintBase

# Helper modules (primarily used internally by BlueprintBase or CLI)
from . import cli_handler, config_loader
from .blueprint_discovery import discover_blueprints
from .blueprint_utils import filter_blueprints

# from . import interactive_mode # If interactive mode is refactored out
# from . import output_utils     # If output utils are used externally

# Re-export essential message utilities if they are part of the public API
# of this extension package. If they are purely internal utilities,
# they don't necessarily need to be re-exported here.
try:
    from swarm.utils.context_utils import truncate_message_history
    from swarm.utils.message_sequence import (
        repair_message_payload,
        validate_message_sequence,
    )
except ImportError as import_error:
    import logging
    error_msg = str(import_error)
    logging.getLogger(__name__).warning(f"Could not import core message utilities: {error_msg}")
    # Define dummy functions or let importers handle the ImportError
    def repair_message_payload(m, **kwargs): raise NotImplementedError(f"repair_message_payload not available: {error_msg}")
    def validate_message_sequence(m): raise NotImplementedError(f"validate_message_sequence not available: {error_msg}")
    def truncate_message_history(m, *args, **kwargs): raise NotImplementedError(f"truncate_message_history not available: {error_msg}")


__all__ = [
    # Core
    "BlueprintBase",
    "discover_blueprints",
    "filter_blueprints",

    # Helper Modules (Exporting for potential external use, though less common)
    "config_loader",
    "cli_handler",
    # "interactive_mode",
    # "output_utils",

    # Utility Functions (If considered part of the public API)
    "repair_message_payload",
    "validate_message_sequence",
    "truncate_message_history",
]
