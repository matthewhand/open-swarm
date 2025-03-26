"""
Utilities for managing context in message histories, including token counting
and truncation strategies.
"""

import logging
import os
import json
from typing import List, Dict, Any

try:
    import tiktoken
except ImportError:
    tiktoken = None
    logging.warning("tiktoken not found. Falling back to approximate token counting (word count).")

logger = logging.getLogger(__name__)

def get_token_count(text: Any, model: str) -> int:
    """
    Calculate token count for a given input (string, dict, list) using tiktoken for the specified model.
    Falls back to approximate word count if tiktoken is unavailable or model is unknown.
    """
    processed_text = ""
    if isinstance(text, str):
        processed_text = text
    elif isinstance(text, (dict, list)):
         try:
              processed_text = json.dumps(text, separators=(',', ':'))
         except TypeError:
              processed_text = str(text) if text is not None else ""
    else:
         processed_text = str(text) if text is not None else ""

    if not processed_text: return 0

    if tiktoken:
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(processed_text))
        except KeyError:
            try:
                 encoding = tiktoken.get_encoding("cl100k_base")
                 return len(encoding.encode(processed_text))
            except Exception as e:
                 logger.error(f"tiktoken encoding failed even with fallback: {e}. Using word count.")
    # Fallback to approximate word count
    return len(processed_text.split())

# --- Truncation Strategies ---

def _truncate_sophisticated(messages: List[Dict[str, Any]], model: str, max_tokens: int, max_messages: int) -> List[Dict[str, Any]]:
    """
    Truncate message history, preserving system messages and assistant/tool pairs.
    Iterates backwards, keeping pairs if they fit within token/message limits.
    """
    system_msgs = []
    non_system_msgs = []
    system_found = False
    for msg in messages:
         if isinstance(msg, dict):
              if msg.get("role") == "system" and not system_found:
                   system_msgs.append(msg)
                   system_found = True
              elif msg.get("role") != "system":
                   non_system_msgs.append(msg)

    system_tokens = sum(get_token_count(msg, model) for msg in system_msgs)
    target_msg_count = max(0, max_messages - len(system_msgs))
    target_token_count = max(0, max_tokens - system_tokens)

    if len(system_msgs) > max_messages or system_tokens > max_tokens:
        logger.warning("System messages alone exceed token/message limits. Returning empty list.")
        return []

    try:
         msg_tokens = [(msg, get_token_count(msg, model)) for msg in non_system_msgs]
    except Exception as e:
         logger.error(f"Error calculating initial tokens for truncation: {e}. Using approximate counts.")
         msg_tokens = [(msg, get_token_count(str(msg.get("content", "")), model) + 10) for msg in non_system_msgs]

    current_total_tokens = sum(t for _, t in msg_tokens)
    if len(non_system_msgs) <= target_msg_count and current_total_tokens <= target_token_count:
        logger.debug(f"History within limits ({len(non_system_msgs)} non-system msgs, {current_total_tokens} tokens). No truncation needed.")
        return system_msgs + non_system_msgs

    logger.debug(f"Sophisticated truncation needed. Current: {len(non_system_msgs)} msgs, {current_total_tokens} tokens. Target: {target_msg_count} msgs, {target_token_count} tokens.")

    truncated = []
    total_tokens = 0
    kept_indices = set()
    i = len(msg_tokens) - 1

    while i >= 0 and len(truncated) < target_msg_count:
        if i in kept_indices:
             i -= 1
             continue

        msg, tokens = msg_tokens[i]
        current_role = msg.get("role")

        # Case 1: Tool message - Find and try to include its assistant pair
        if current_role == "tool" and "tool_call_id" in msg:
            tool_call_id = msg["tool_call_id"]
            assistant_idx = i - 1
            pair_found_and_added = False
            search_depth = 0
            max_search_depth = 10 # Limit how far back we look for the assistant

            while assistant_idx >= 0 and search_depth < max_search_depth:
                 if assistant_idx in kept_indices:
                      assistant_idx -= 1
                      search_depth += 1
                      continue

                 prev_msg, prev_tokens = msg_tokens[assistant_idx]
                 if prev_msg.get("role") == "assistant" and prev_msg.get("tool_calls"):
                     if any(tc.get("id") == tool_call_id for tc in prev_msg.get("tool_calls", []) if isinstance(tc, dict)):
                          pair_total_tokens = tokens + prev_tokens
                          if total_tokens + pair_total_tokens <= target_token_count and len(truncated) + 2 <= target_msg_count:
                               truncated.insert(0, prev_msg)
                               truncated.insert(1, msg)
                               total_tokens += pair_total_tokens
                               kept_indices.add(i)
                               kept_indices.add(assistant_idx)
                               pair_found_and_added = True
                               logger.debug(f"  Kept pair: Assistant (idx {assistant_idx}, {prev_tokens} tokens) + Tool (idx {i}, {tokens} tokens). New total tokens: {total_tokens}")
                               i = assistant_idx - 1 # Continue search before the added assistant
                               break # Stop inner search
                          else:
                               logger.debug(f"  Pair for tool {tool_call_id} (idx {i}) found but doesn't fit limits (Tokens: {total_tokens + pair_total_tokens}/{target_token_count}, Msgs: {len(truncated) + 2}/{target_msg_count}). Skipping pair.")
                               break # Stop inner search

                 # Stop searching backwards if a user message is encountered
                 if prev_msg.get("role") == "user":
                      break

                 assistant_idx -= 1
                 search_depth += 1

            if not pair_found_and_added:
                 logger.debug(f"  Skipping lone tool message (idx {i}, ID {tool_call_id}) as pair not found or didn't fit.")
                 i -= 1 # Move to the message before the lone tool message

        # Case 2: Assistant message with tool calls - Find and try to include its tool(s)
        elif current_role == "assistant" and isinstance(msg.get("tool_calls"), list):
             assistant_msg = msg
             assistant_tokens = tokens
             expected_tool_ids = {tc.get("id") for tc in assistant_msg.get("tool_calls", []) if isinstance(tc, dict)}
             found_tools_data = []
             indices_of_found_tools = []
             temp_tool_tokens = 0

             j = i + 1
             while j < len(msg_tokens):
                  tool_msg, tool_tokens = msg_tokens[j]
                  tool_msg_call_id = tool_msg.get("tool_call_id")

                  if tool_msg.get("role") == "tool" and tool_msg_call_id in expected_tool_ids:
                      if j not in kept_indices:
                           found_tools_data.append((tool_msg, tool_tokens))
                           indices_of_found_tools.append(j)
                           temp_tool_tokens += tool_tokens
                  elif tool_msg.get("role") != "tool": # Stop if not a tool message
                      break
                  j += 1

             pair_tokens = assistant_tokens + temp_tool_tokens
             pair_len = 1 + len(found_tools_data)

             if total_tokens + pair_tokens <= target_token_count and len(truncated) + pair_len <= target_msg_count:
                  truncated.insert(0, assistant_msg)
                  kept_indices.add(i)
                  tool_insert_index = 1
                  for tool_idx, (tool_d_msg, tool_d_tokens) in zip(indices_of_found_tools, found_tools_data):
                       truncated.insert(tool_insert_index, tool_d_msg)
                       kept_indices.add(tool_idx)
                       tool_insert_index += 1
                  total_tokens += pair_tokens
                  logger.debug(f"  Kept pair: Assistant (idx {i}, {assistant_tokens} tokens) + {len(found_tools_data)} Tools ({temp_tool_tokens} tokens). New total tokens: {total_tokens}")
                  i -= 1
             else:
                  logger.debug(f"  Skipping assistant message (idx {i}) and its tools as pair exceeds limits (Tokens: {total_tokens + pair_tokens}/{target_token_count}, Msgs: {len(truncated) + pair_len}/{target_msg_count}).")
                  i -= 1

        # Case 3: Regular message (user, or assistant without tool calls)
        else:
             if total_tokens + tokens <= target_token_count and len(truncated) < target_msg_count:
                  truncated.insert(0, msg)
                  total_tokens += tokens
                  kept_indices.add(i)
                  logger.debug(f"  Kept message (idx {i}, role {current_role}, {tokens} tokens). New total tokens: {total_tokens}")
                  i -= 1
             else:
                  logger.debug(f"  Stopping truncation: Message {i} ({current_role}) doesn't fit limits (Tokens: {total_tokens+tokens}/{target_token_count}, Msgs: {len(truncated)+1}/{target_msg_count}).")
                  break

    final_messages = system_msgs + truncated
    final_token_check = sum(get_token_count(m, model) for m in final_messages)
    logger.debug(f"Sophisticated truncation result: {len(final_messages)} messages ({len(system_msgs)} sys, {len(truncated)} non-sys), {final_token_check} tokens.")
    return final_messages


def _truncate_simple(messages: List[Dict[str, Any]], model: str, max_tokens: int, max_messages: int) -> List[Dict[str, Any]]:
    """Simple truncation keeping the system message and the most recent messages within limits."""
    # (Implementation remains the same as before)
    system_msgs = []
    non_system_msgs = []
    system_found = False
    for msg in messages:
         if isinstance(msg, dict):
              if msg.get("role") == "system" and not system_found:
                   system_msgs.append(msg)
                   system_found = True
              elif msg.get("role") != "system":
                   non_system_msgs.append(msg)

    system_tokens = sum(get_token_count(msg, model) for msg in system_msgs)
    target_msg_count = max(0, max_messages - len(system_msgs))
    target_token_count = max(0, max_tokens - system_tokens)

    if len(system_msgs) > max_messages or system_tokens > max_tokens:
        logger.warning("System messages alone exceed token/message limits. Returning empty list.")
        return []

    result_non_system = []
    current_tokens = 0
    current_msg_count = 0
    # logger.debug(f"_truncate_simple: Target tokens={target_token_count}, Target msgs={target_msg_count}")
    for msg_index, msg in reversed(list(enumerate(non_system_msgs))):
        msg_tokens = get_token_count(msg, model)
        # logger.debug(f"  Considering msg {msg_index} (role={msg.get('role')}): cost={msg_tokens} tokens. Current totals: {current_msg_count}/{target_msg_count} msgs, {current_tokens}/{target_token_count} tokens.")

        if (current_msg_count + 1 <= target_msg_count and
                current_tokens + msg_tokens <= target_token_count):
            result_non_system.append(msg)
            current_tokens += msg_tokens
            current_msg_count += 1
            # logger.debug(f"    Kept msg {msg_index}. New totals: {current_msg_count}/{target_msg_count} msgs, {current_tokens}/{target_token_count} tokens.")
        else:
            # logger.debug(f"    Stopping at msg {msg_index}: Adding it would exceed limits (tokens: {current_tokens + msg_tokens} > {target_token_count} or count: {current_msg_count + 1} > {target_msg_count}).")
            break

    final_result = system_msgs + list(reversed(result_non_system))
    final_token_check = sum(get_token_count(m, model) for m in final_result)
    logger.debug(f"Simple truncation result: {len(final_result)} messages ({len(system_msgs)} sys), {final_token_check} tokens.")
    return final_result


def truncate_message_history(messages: List[Dict[str, Any]], model: str, max_tokens: int, max_messages: int) -> List[Dict[str, Any]]:
    """
    Truncate message history based on token and message limits.
    Uses sophisticated pair-preserving mode if SWARM_TRUNCATION_MODE=pairs, otherwise simple mode.
    """
    if not messages: return []

    truncation_mode = os.getenv("SWARM_TRUNCATION_MODE", "pairs").lower() # Default to pairs
    mode_name = f"Sophisticated (Pair-Preserving)" if truncation_mode == "pairs" else "Simple (Recent Only)"
    logger.debug(f"Truncating message history. Mode: {mode_name}, Max Tokens: {max_tokens}, Max Messages: {max_messages}")

    try:
        if truncation_mode == "pairs":
             result = _truncate_sophisticated(messages, model, max_tokens, max_messages)
        else: # Default to simple if not "pairs"
            if truncation_mode != "simple":
                 logger.warning(f"Unknown SWARM_TRUNCATION_MODE '{truncation_mode}'. Defaulting to 'simple'.")
            result = _truncate_simple(messages, model, max_tokens, max_messages)
    except Exception as e:
        logger.error(f"Error during message truncation: {e}", exc_info=True)
        try:
             logger.warning("Falling back to simple truncation due to error.")
             result = _truncate_simple(messages, model, max_tokens, max_messages)
        except Exception:
             logger.error("Fallback simple truncation also failed. Returning raw last messages.")
             system_msg = [m for m in messages if isinstance(m, dict) and m.get("role") == "system"]
             non_system_msgs = [m for m in messages if not (isinstance(m, dict) and m.get("role") == "system")]
             keep_count = max(0, max_messages - len(system_msg))
             result = system_msg + non_system_msgs[-keep_count:]

    # Final check for emptiness
    if messages and not result:
         system_msgs_in_input = [m for m in messages if isinstance(m, dict) and m.get("role") == "system"]
         system_tokens_in_input = sum(get_token_count(msg, model) for msg in system_msgs_in_input)
         if len(system_msgs_in_input) > max_messages or system_tokens_in_input > max_tokens:
              logger.warning("Truncation resulted in empty list, likely due to system message exceeding limits.")
              return []
         else:
             logger.warning("Truncation resulted in empty list despite positive limits, returning last message as fallback.")
             last_msg = messages[-1:]
             last_tokens = get_token_count(last_msg[0], model) if last_msg and isinstance(last_msg[0], dict) else 0
             return last_msg if len(last_msg) <= max_messages and last_tokens <= max_tokens else []

    return result
