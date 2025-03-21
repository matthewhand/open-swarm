"""
Common utilities for blueprint extensions.
"""

from typing import Any, Dict, List

def get_agent_name(agent: Any) -> str:
    """Return the name of an agent from its attributes."""
    return getattr(agent, "name", getattr(agent, "__name__", "<unknown>"))

def get_token_count(messages: List[Dict[str, Any]], model: str) -> int:
    """
    Estimate token count for messages (placeholder; replace with an actual implementation).
    Rough estimate: 4 characters ≈ 1 token.
    """
    return sum(len(msg.get("content") or "") // 4 for msg in messages)