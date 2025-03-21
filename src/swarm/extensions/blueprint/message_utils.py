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

def get_token_count(messages: List[Dict[str, Any]], model: str) -> int:
    """Estimate token count for messages (placeholder—replace with actual implementation)."""
    return sum(len(msg.get("content") or "") // 4 for msg in messages)

def truncate_preserve_pairs(messages: List[Dict[str, Any]], model: str, max_context_tokens: int, max_context_messages: int) -> List[Dict[str, Any]]:
    system_msgs = [msg for msg in messages if msg.get("role") == "system"]
    non_system_msgs = [msg for msg in messages if msg.get("role") != "system"]
    current_tokens = get_token_count(non_system_msgs, model)
    if len(non_system_msgs) <= max_context_messages and current_tokens <= max_context_tokens:
        return system_msgs + non_system_msgs
    msg_tokens = [(msg, get_token_count([msg], model)) for msg in non_system_msgs]
    total_tokens = 0
    truncated = []
    i = len(msg_tokens) - 1
    while i >= 0 and len(truncated) < max_context_messages:
        msg, tokens = msg_tokens[i]
        if msg.get("role") == "tool" and "tool_call_id" in msg:
            tool_call_id = msg["tool_call_id"]
            assistant_idx = i - 1
            pair_found = False
            while assistant_idx >= 0:
                prev_msg, prev_tokens = msg_tokens[assistant_idx]
                if prev_msg.get("role") == "assistant" and "tool_calls" in prev_msg:
                    for tc in prev_msg["tool_calls"]:
                        if tc["id"] == tool_call_id and total_tokens + tokens + prev_tokens <= max_context_tokens and len(truncated) + 2 <= max_context_messages:
                            truncated.insert(0, prev_msg)
                            truncated.insert(1, msg)
                            total_tokens += tokens + prev_tokens
                            pair_found = True
                            break
                if pair_found:
                    break
                assistant_idx -= 1
        elif msg.get("role") == "assistant" and "tool_calls" in msg:
            tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
            tool_msgs = []
            j = i + 1
            while j < len(msg_tokens) and tool_call_ids:
                next_msg, next_tokens = msg_tokens[j]
                if next_msg.get("role") == "tool" and next_msg.get("tool_call_id") in tool_call_ids:
                    tool_msgs.append((next_msg, next_tokens))
                    tool_call_ids.remove(next_msg["tool_call_id"])
                else:
                    break
                j += 1
            pair_tokens = tokens + sum(t for _, t in tool_msgs)
            pair_len = 1 + len(tool_msgs)
            if total_tokens + pair_tokens <= max_context_tokens and len(truncated) + pair_len <= max_context_messages:
                truncated.insert(0, msg)
                for tool_msg, _ in tool_msgs:
                    truncated.insert(1, tool_msg)
                total_tokens += pair_tokens
        elif total_tokens + tokens <= max_context_tokens and len(truncated) < max_context_messages:
            truncated.insert(0, msg)
            total_tokens += tokens
        i -= 1
    final_messages = system_msgs + truncated
    return final_messages

def truncate_strict_token(messages: List[Dict[str, Any]], model: str, max_context_tokens: int, max_context_messages: int) -> List[Dict[str, Any]]:
    system_msgs = [msg for msg in messages if msg.get("role") == "system"]
    non_system_msgs = [msg for msg in messages if msg.get("role") != "system"]
    msg_tokens = [(msg, get_token_count([msg], model)) for msg in non_system_msgs]
    total_tokens = 0
    truncated = []
    i = len(msg_tokens) - 1
    while i >= 0 and len(truncated) < max_context_messages:
        msg, tokens = msg_tokens[i]
        if msg.get("role") == "tool" and "tool_call_id" in msg:
            tool_call_id = msg["tool_call_id"]
            assistant_idx = i - 1
            pair_found = False
            while assistant_idx >= 0:
                prev_msg, prev_tokens = msg_tokens[assistant_idx]
                if prev_msg.get("role") == "assistant" and "tool_calls" in prev_msg:
                    for tc in prev_msg["tool_calls"]:
                        if tc["id"] == tool_call_id and total_tokens + tokens + prev_tokens <= max_context_tokens and len(truncated) + 2 <= max_context_messages:
                            truncated.insert(0, prev_msg)
                            truncated.insert(1, msg)
                            total_tokens += tokens + prev_tokens
                            pair_found = True
                            break
                if pair_found:
                    break
                assistant_idx -= 1
        elif msg.get("role") == "assistant" and "tool_calls" in msg:
            tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
            tool_msgs = []
            j = i + 1
            while j < len(msg_tokens) and tool_call_ids:
                next_msg, next_tokens = msg_tokens[j]
                if next_msg.get("role") == "tool" and next_msg.get("tool_call_id") in tool_call_ids:
                    tool_msgs.append((next_msg, next_tokens))
                    tool_call_ids.remove(next_msg["tool_call_id"])
                else:
                    break
                j += 1
            pair_tokens = tokens + sum(t for _, t in tool_msgs)
            pair_len = 1 + len(tool_msgs)
            if total_tokens + pair_tokens <= max_context_tokens and len(truncated) + pair_len <= max_context_messages:
                truncated.insert(0, msg)
                for tool_msg, _ in tool_msgs:
                    truncated.insert(1, tool_msg)
                total_tokens += pair_tokens
        elif total_tokens + tokens <= max_context_tokens and len(truncated) < max_context_messages:
            truncated.insert(0, msg)
            total_tokens += tokens
        i -= 1
    final_messages = system_msgs + truncated
    return final_messages

def truncate_recent_only(messages: List[Dict[str, Any]], model: str, max_context_messages: int) -> List[Dict[str, Any]]:
    system_msgs = [msg for msg in messages if msg.get("role") == "system"]
    non_system_msgs = [msg for msg in messages if msg.get("role") != "system"]
    msg_tokens = [(msg, get_token_count([msg], model)) for msg in non_system_msgs]
    truncated = []
    i = len(msg_tokens) - 1
    while i >= 0 and len(truncated) < max_context_messages:
        msg, _ = msg_tokens[i]
        if msg.get("role") == "tool" and "tool_call_id" in msg:
            tool_call_id = msg["tool_call_id"]
            assistant_idx = i - 1
            pair_found = False
            while assistant_idx >= 0:
                prev_msg, _ = msg_tokens[assistant_idx]
                if prev_msg.get("role") == "assistant" and "tool_calls" in prev_msg:
                    for tc in prev_msg["tool_calls"]:
                        if tc["id"] == tool_call_id and len(truncated) + 2 <= max_context_messages:
                            truncated.insert(0, prev_msg)
                            truncated.insert(1, msg)
                            pair_found = True
                            break
                if pair_found:
                    break
                assistant_idx -= 1
        elif msg.get("role") == "assistant" and "tool_calls" in msg:
            tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
            tool_msgs = []
            j = i + 1
            while j < len(msg_tokens) and tool_call_ids:
                next_msg, _ = msg_tokens[j]
                if next_msg.get("role") == "tool" and next_msg.get("tool_call_id") in tool_call_ids:
                    tool_msgs.append(next_msg)
                    tool_call_ids.remove(next_msg["tool_call_id"])
                else:
                    break
                j += 1
            pair_len = 1 + len(tool_msgs)
            if len(truncated) + pair_len <= max_context_messages:
                truncated.insert(0, msg)
                for tool_msg in tool_msgs:
                    truncated.insert(1, tool_msg)
        elif len(truncated) < max_context_messages:
            truncated.insert(0, msg)
        i -= 1
    final_messages = system_msgs + truncated
    return final_messages