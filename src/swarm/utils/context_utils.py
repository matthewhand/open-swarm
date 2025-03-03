"""
Swarm Context Utils

This module provides utility functions for managing conversational context in the Swarm framework,
including token counting and message truncation.
"""

import logging
from typing import List, Dict, Any

import tiktoken
import os
import json

logger = logging.getLogger(__name__)

def get_token_count(messages: List[Dict[str, Any]], model: str) -> int:
    """
    Calculate the total token count for a list of messages.
    For 'dummy-model', use a simple whitespace split heuristic.
    Otherwise, use tiktoken encoding.
    """
    if model == "dummy-model":
        total_tokens = 0
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, str):
                total_tokens += len(content.split())
        logger.debug(f"Total token count for messages (dummy): {total_tokens}")
        return total_tokens

    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning(f"Encoding not found for model '{model}'. Using 'cl100k_base' as fallback.")
        encoding = tiktoken.get_encoding("cl100k_base")
    
    total_tokens = 0
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            total_tokens += len(encoding.encode(content))
        # Add overhead unless using dummy model
        total_tokens += 4
        if "tool_calls" in message and message["tool_calls"] is not None:
            for tool_call in message["tool_calls"]:
                total_tokens += len(encoding.encode(json.dumps(tool_call)))
    logger.debug(f"Total token count for messages: {total_tokens}")
    return total_tokens
def truncate_message_history(messages: List[Dict[str, Any]], model: str, max_tokens: int = None, max_messages: int = None) -> List[Dict[str, Any]]:
    if max_tokens is None:
        max_tokens = int(os.getenv("MAX_OUTPUT", "1000"))
    if max_messages is None:
        max_messages = 100
    system_messages = [msg for msg in messages if msg.get("role") == "system"]
    non_system_messages = [msg for msg in messages if msg.get("role") != "system"]
    current_token_count = get_token_count(non_system_messages, model)
    if len(non_system_messages) <= max_messages and current_token_count <= max_tokens:
        logger.debug(f"Message history within limits: {len(non_system_messages)} messages, {current_token_count} tokens")
        return system_messages + non_system_messages
    truncated = []
    running_total = 0
    for msg in reversed(non_system_messages):
        t = get_token_count([msg], model)
        if running_total + t <= max_tokens and len(truncated) < max_messages:
            truncated.insert(0, msg)
            running_total += t
        else:
            break
    return system_messages + truncated
