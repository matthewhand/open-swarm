"""
Blueprint Extension Package for Open Swarm.

Provides the base class, discovery mechanisms, and utilities for creating
and running autonomous agent workflows (blueprints).
"""

# Core components
from .blueprint_base import BlueprintBase
from .blueprint_discovery import discover_blueprints
from .blueprint_utils import filter_blueprints

# Helper modules (primarily used internally by BlueprintBase or CLI)
from . import config_loader
from . import cli_handler
# from . import interactive_mode # If interactive mode is refactored out
# from . import output_utils     # If output utils are used externally

# Re-export essential message utilities if they are part of the public API
# of this extension package. If they are purely internal utilities,
# they don't necessarily need to be re-exported here.
try:
    from swarm.utils.message_sequence import repair_message_payload, validate_message_sequence
    from swarm.utils.context_utils import truncate_message_history
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Could not import core message utilities: {e}")
    # Define dummy functions or let importers handle the ImportError
    def repair_message_payload(m, **kwargs): raise NotImplementedError from e
    def validate_message_sequence(m): raise NotImplementedError from e
    def truncate_message_history(m, *args, **kwargs): raise NotImplementedError from e


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

