"""
Blueprint discovery and management utilities.
"""

from .blueprint_base import BlueprintBase
from .blueprint_discovery import discover_blueprints
from .blueprint_utils import filter_blueprints

# Re-export the necessary message utilities from their new locations
# Note: The specific truncation functions like truncate_preserve_pairs might have been
# consolidated into truncate_message_history. Adjust if needed.
try:
    from swarm.utils.message_sequence import repair_message_payload, validate_message_sequence
    from swarm.utils.context_utils import truncate_message_history
    # If specific old truncation functions are truly needed, they'd have to be
    # re-implemented or their callers refactored to use truncate_message_history.
    # Assuming truncate_message_history is the intended replacement for now.
    # Define aliases if old names are required by downstream code:
    # truncate_preserve_pairs = truncate_message_history # Example if needed
except ImportError as e:
    # Log an error or warning if imports fail, helpful for debugging setup issues
    import logging
    logging.getLogger(__name__).error(f"Failed to import core message utilities: {e}")
    # Define dummy functions or raise error if critical
    def repair_message_payload(m, **kwargs): return m
    def validate_message_sequence(m): return m
    def truncate_message_history(m, *args, **kwargs): return m

__all__ = [
    "BlueprintBase",
    "discover_blueprints",
    "filter_blueprints",
    "repair_message_payload",
    "validate_message_sequence",
    "truncate_message_history",
]
