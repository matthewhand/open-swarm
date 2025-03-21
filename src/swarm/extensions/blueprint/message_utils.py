"""
Utilities for repairing message payloads specific to blueprint extensions.
"""

import json
import logging
from typing import List, Dict, Any

try:
    from swarm.utils.message_utils import filter_duplicate_system_messages
except ImportError:
    def filter_duplicate_system_messages(messages):
        return messages

logger = logging.getLogger(__name__)

def repair_message_payload(messages: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
    """
    Repair the message sequence by reordering tool messages after their corresponding calls.
    
    Args:
        messages: List of messages to repair.
        debug: If True, log detailed repair information.
    
    Returns:
        List[Dict[str, Any]]: Repaired message sequence.
    """
    if not isinstance(messages, list):
        logger.error(f"Invalid messages type for repair: {type(messages)}. Returning empty list.")
        return []
    
    logger.debug(f"Repairing message payload with {len(messages)} messages")
    messages = filter_duplicate_system_messages(messages)
    valid_tool_call_ids = {
        tc["id"]
        for msg in messages
        if msg.get("role") == "assistant" and isinstance(msg.get("tool_calls"), list)
        for tc in msg.get("tool_calls", []) if isinstance(tc, dict) and "id" in tc
    }
    repaired = [
        msg for msg in messages 
        if msg.get("role") != "tool" or msg.get("tool_call_id") in valid_tool_call_ids
    ]
    final_sequence = []
    i = 0
    while i < len(repaired):
        msg = repaired[i]
        if msg.get("role") == "assistant" and "tool_calls" in msg and msg["tool_calls"]:
            # Extract tool_call ids from the assistant message
            tool_call_ids = [tc.get("id") for tc in msg["tool_calls"] if isinstance(tc, dict) and "id" in tc]
            final_sequence.append(msg)
            j = i + 1
            missing_ids = set(tool_call_ids)
            # Scan following messages for tool responses
            while j < len(repaired) and repaired[j].get("role") == "tool":
                t_id = repaired[j].get("tool_call_id")
                if t_id in missing_ids:
                    missing_ids.remove(t_id)
                final_sequence.append(repaired[j])
                j += 1
            # For any tool_call id without a corresponding tool message, insert a dummy tool response
            for missing_id in missing_ids:
                dummy_tool = {
                    "role": "tool",
                    "tool_call_id": missing_id,
                    "tool_name": "dummy_response",
                    "content": ""
                }
                final_sequence.append(dummy_tool)
            i = j
        elif msg.get("role") == "tool":
            # If a tool message appears without a preceding assistant message with tool_calls, create a dummy assistant entry
            tool_call_id = msg.get("tool_call_id")
            dummy_assistant = {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": tool_call_id, "name": msg.get("tool_name", "unnamed_tool")}]
            }
            final_sequence.append(dummy_assistant)
            final_sequence.append(msg)
            i += 1
        else:
            final_sequence.append(msg)
            i += 1
    if debug:
        logger.debug(f"Repaired payload: {json.dumps(final_sequence, indent=2, default=str)}")
    return final_sequence

def validate_message_sequence(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure tool messages correspond to valid tool calls in the sequence.
    
    Args:
        messages: List of messages to validate.
    
    Returns:
        List[Dict[str, Any]]: Validated and filtered message sequence.
    """
    if not isinstance(messages, list):
        logger.error(f"Invalid messages type for validation: {type(messages)}. Returning empty list.")
        return []
    logger.debug(f"Validating message sequence with {len(messages)} messages")
    valid_tool_call_ids = {
        tc["id"]
        for msg in messages
        if msg.get("role") == "assistant"
        for tc in (msg.get("tool_calls") or [])
        if isinstance(tc, dict) and "id" in tc
    }
    return [msg for msg in messages if msg.get("role") != "tool" or msg.get("tool_call_id") in valid_tool_call_ids]