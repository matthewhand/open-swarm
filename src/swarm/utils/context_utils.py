"""
Swarm Context Utils

This module provides utility functions for managing conversational context in the Swarm framework,
including token counting and message truncation. Summarization is handled in core.py to avoid circular imports.
"""

import logging
from typing import List, Dict, Any

import tiktoken

logger = logging.getLogger(__name__)

def get_token_count(messages: List[Dict[str, Any]], model: str) -> int:
    """Calculate the total token count for a list of messages using the model's encoding."""
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
        # Add approximate tokens for role and structure
        total_tokens += 4  # Rough estimate for role and separators
        if "tool_calls" in message:
            for tool_call in message["tool_calls"]:
                total_tokens += len(encoding.encode(json.dumps(tool_call)))
    logger.debug(f"Total token count for messages: {total_tokens}")
    return total_tokens

def truncate_message_history(messages: List[Dict[str, Any]], model: str, max_tokens: int, max_messages: int) -> List[Dict[str, Any]]:
    """
    Truncate message history to fit within token and message limits, preserving assistant-tool message pairs.
    """
    if not messages:
        logger.debug("No messages to truncate.")
        return messages

    # Separate system messages (preserve these)
    system_messages = [msg for msg in messages if msg["role"] == "system"]
    non_system_messages = [msg for msg in messages if msg["role"] != "system"]

    # Early exit if within limits
    current_token_count = get_token_count(messages, model)
    if len(non_system_messages) <= max_messages and current_token_count <= max_tokens:
        logger.debug(f"Message history within limits: {len(non_system_messages)} messages, {current_token_count} tokens")
        return messages

    # Pre-calculate token counts for each message
    message_tokens = [(msg, get_token_count([msg], model)) for msg in non_system_messages]
    total_tokens = sum(tokens for _, tokens in message_tokens)

    # Truncate from oldest to newest, preserving assistant-tool pairs
    truncated = []
    i = len(message_tokens) - 1
    while i >= 0 and (len(truncated) < max_messages and total_tokens <= max_tokens):
        msg, tokens = message_tokens[i]
        if msg["role"] == "tool":
            # Look for preceding assistant message with matching tool_call_id
            tool_call_id = msg.get("tool_call_id")
            assistant_idx = i - 1
            assistant_found = False
            while assistant_idx >= 0:
                prev_msg, prev_tokens = message_tokens[assistant_idx]
                if prev_msg["role"] == "assistant" and "tool_calls" in prev_msg:
                    for tc in prev_msg["tool_calls"]:
                        if tc["id"] == tool_call_id:
                            if total_tokens + prev_tokens <= max_tokens and len(truncated) + 2 <= max_messages:
                                truncated.insert(0, prev_msg)
                                truncated.insert(1, msg)
                                total_tokens += tokens + prev_tokens
                            assistant_found = True
                            break
                if assistant_found:
                    break
                assistant_idx -= 1
            if not assistant_found:
                logger.debug(f"Skipping orphaned tool message with tool_call_id '{tool_call_id}'")
        elif msg["role"] == "assistant" and "tool_calls" in msg:
            # Include assistant and all following tool messages
            tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
            tool_msgs = []
            j = i + 1
            while j < len(message_tokens):
                next_msg, next_tokens = message_tokens[j]
                if next_msg["role"] == "tool" and next_msg.get("tool_call_id") in tool_call_ids:
                    tool_msgs.append((next_msg, next_tokens))
                    tool_call_ids.remove(next_msg["tool_call_id"])
                else:
                    break
                j += 1
            if total_tokens + tokens + sum(t for _, t in tool_msgs) <= max_tokens and len(truncated) + 1 + len(tool_msgs) <= max_messages:
                truncated.insert(0, msg)
                for tool_msg, tool_tokens in tool_msgs:
                    truncated.insert(1, tool_msg)
                total_tokens += tokens + sum(t for _, t in tool_msgs)
            else:
                logger.debug(f"Skipping assistant message with tool_calls due to token/message limits")
        else:
            # Non-tool-related message
            if total_tokens + tokens <= max_tokens and len(truncated) < max_messages:
                truncated.insert(0, msg)
                total_tokens += tokens
        i -= 1

    final_messages = system_messages + truncated
    logger.debug(f"Truncated to {len(final_messages)} messages with {total_tokens} tokens")
    return final_messages
