"""
Common utilities potentially shared across blueprint extensions.
"""

from typing import Any # Removed Dict, List as they weren't used

def get_agent_name(agent: Any) -> str:
    """Return the name of an agent from its attributes ('name' or '__name__')."""
    return getattr(agent, "name", getattr(agent, "__name__", "<unknown>"))

# get_token_count has been moved to swarm.utils.context_utils
# Ensure imports in other files point to the correct location.
