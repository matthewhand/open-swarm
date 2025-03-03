"""
Utility functions for processing chat messages in the Swarm framework.
"""

import logging

logger = logging.getLogger(__name__)

def filter_duplicate_system_messages(messages):
    """Remove duplicate system messages, keeping only the first occurrence."""
    filtered = []
    system_found = False
    for msg in messages:
        if msg.get("role") == "system":
            if system_found:
                continue
            system_found = True
        filtered.append(msg)
    return filtered

def filter_messages(messages):
    """Filter out messages with None content."""
    return [msg for msg in messages if msg.get('content') is not None]

def update_null_content(messages):
    """Replace None content with empty string in messages."""
    for msg in messages:
        if msg.get('content') is None:
            msg['content'] = ""
    return messages
