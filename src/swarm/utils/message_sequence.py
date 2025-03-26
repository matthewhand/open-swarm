"""
Utilities for validating and repairing message sequences.
"""

from typing import List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

try:
    from .message_utils import filter_duplicate_system_messages
except ImportError:
    try: from swarm.utils.message_utils import filter_duplicate_system_messages
    except ImportError:
        logger.warning("filter_duplicate_system_messages not found. Using dummy.")
        def filter_duplicate_system_messages(messages):
            output = []; system_found = False
            for msg in messages:
                if isinstance(msg, dict) and msg.get("role") == "system":
                    if not system_found: output.append(msg); system_found = True
                # *** Fix in dummy: Append non-dicts too if needed, or filter here?
                # Let's assume the filter should focus only on system duplicates for now.
                elif not (isinstance(msg, dict) and msg.get("role") == "system"):
                     output.append(msg)
            return output

def validate_message_sequence(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure tool messages correspond to valid tool calls in the sequence.
    Also filters out non-dictionary items.
    """
    if not isinstance(messages, list):
        logger.error(f"Invalid messages type for validation: {type(messages)}. Returning [].")
        return []
    logger.debug(f"Validating message sequence with {len(messages)} messages")

    # *** FIX: Filter non-dicts FIRST ***
    dict_messages = [msg for msg in messages if isinstance(msg, dict)]
    if len(dict_messages) < len(messages):
        logger.warning(f"Removed {len(messages) - len(dict_messages)} non-dictionary items during validation.")

    try:
        # *** FIX: Operate ONLY on dict_messages ***
        valid_tool_call_ids = {
            tc["id"]
            for msg in dict_messages # Use filtered list
            if msg.get("role") == "assistant" and isinstance(msg.get("tool_calls"), list)
            for tc in msg.get("tool_calls", [])
            if isinstance(tc, dict) and "id" in tc
        }
    except Exception as e:
        logger.error(f"Error building valid_tool_call_ids: {e}", exc_info=True)
        valid_tool_call_ids = set()

    validated_messages = []
    # *** FIX: Operate ONLY on dict_messages ***
    for msg in dict_messages:
        role = msg.get("role")
        if role == "tool":
            tool_call_id = msg.get("tool_call_id")
            if tool_call_id in valid_tool_call_ids:
                validated_messages.append(msg)
            else:
                logger.warning(f"Removing orphan tool message: {str(msg)[:100]}")
        # *** FIX: Add basic check for other essential roles before appending ***
        elif role in ["system", "user", "assistant"]:
             # We could add more role-specific checks here if needed (like _is_valid_message)
             # For now, just ensure it's one of the expected roles.
             validated_messages.append(msg)
        else:
             logger.warning(f"Removing message with unknown/missing role during validation: {str(msg)[:100]}")


    return validated_messages

def repair_message_payload(messages: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
    """
    Repair the message sequence by potentially inserting dummy messages for missing pairs.
    Filters invalid messages and orphan tools first.
    """
    if not isinstance(messages, list):
        logger.error(f"Invalid messages type for repair: {type(messages)}. Returning [].")
        return []
    logger.debug(f"Repairing message payload with {len(messages)} messages")

    try:
        messages_no_dup_sys = filter_duplicate_system_messages(messages)
    except Exception as e:
        logger.error(f"Error during filter_duplicate_system_messages: {e}. Proceeding.")
        messages_no_dup_sys = messages

    # Run validation which now correctly handles non-dicts first
    repaired_validated = validate_message_sequence(messages_no_dup_sys)
    logger.debug(f"After validation, {len(repaired_validated)} messages remain for repair loop.")


    final_sequence = []
    i = 0
    processed_tool_ids = set()

    while i < len(repaired_validated):
        msg = repaired_validated[i]
        role = msg.get("role") # Should always be a valid dict here

        if role == "assistant" and isinstance(msg.get("tool_calls"), list) and msg["tool_calls"]:
            logger.debug(f"Repair Loop: Processing assistant at index {i}")
            final_sequence.append(msg)
            tool_calls = msg["tool_calls"]
            expected_ids = {tc.get("id") for tc in tool_calls if isinstance(tc, dict) and tc.get("id")}

            j = i + 1
            found_ids_for_this_call = set()
            logger.debug(f"  Looking ahead for tools from index {j}. Expected IDs: {expected_ids}")
            while j < len(repaired_validated) and repaired_validated[j].get("role") == "tool":
                tool_msg = repaired_validated[j]
                tool_call_id = tool_msg.get("tool_call_id")
                logger.debug(f"  Checking tool at index {j} (ID: {tool_call_id})")
                if tool_call_id in expected_ids:
                    final_sequence.append(tool_msg)
                    found_ids_for_this_call.add(tool_call_id)
                    processed_tool_ids.add(tool_call_id)
                    logger.debug(f"    Found and appended expected tool response.")
                else:
                    logger.debug(f"    Tool ID does not match current assistant call. Stopping lookahead.")
                    break
                j += 1

            missing_ids_for_this_call = expected_ids - found_ids_for_this_call
            if missing_ids_for_this_call:
                logger.warning(f"  Missing {len(missing_ids_for_this_call)} tool responses for assistant call {i}. IDs: {missing_ids_for_this_call}. Inserting dummies.")
                for missing_id in missing_ids_for_this_call:
                    tool_name = "unknown_tool"
                    for tc in tool_calls:
                        if isinstance(tc, dict) and tc.get("id") == missing_id:
                           tool_name = tc.get("function", {}).get("name", "unknown_tool"); break
                    dummy_tool = {"role": "tool", "tool_call_id": missing_id, "name": tool_name, "content": f"Error: Tool response for {tool_name} missing."} # Use name field like T1_RESP
                    logger.debug(f"    Appending dummy tool: {dummy_tool}")
                    final_sequence.append(dummy_tool)
                    processed_tool_ids.add(missing_id)
            # else:
                 # logger.debug(f"  All tool responses found for assistant call {i}.")

            i = j # Move main index past assistant and its processed tools

        elif role == "tool":
            # This case handles tools that were *not* removed by validation (meaning their ID exists somewhere)
            # but were not found immediately after their corresponding assistant call by the lookahead above.
            # OR tools whose assistant call was completely missing/invalid.
            tool_call_id = msg.get("tool_call_id")
            if tool_call_id in processed_tool_ids:
                 logger.debug(f"Repair Loop: Skipping tool msg at index {i} (id: {tool_call_id}), already processed.")
                 i += 1
            else:
                # Insert a dummy assistant call before it
                logger.warning(f"Repair Loop: Found tool msg {i} (id: {tool_call_id}) without preceding assistant. Inserting dummy assistant.")
                tool_name = msg.get("name", "unknown_tool") # Get tool name from tool message itself
                dummy_assistant = {"role": "assistant", "content": None, "tool_calls": [{"id": tool_call_id, "type": "function", "function": {"name": tool_name, "arguments": "{}"}}]}
                final_sequence.append(dummy_assistant)
                final_sequence.append(msg)
                processed_tool_ids.add(tool_call_id)
                i += 1
        else:
            # System or User message
            logger.debug(f"Repair Loop: Processing {role} at index {i}")
            final_sequence.append(msg)
            i += 1

    if debug: logger.debug(f"Repaired payload: {json.dumps(final_sequence, indent=2, default=str)}")
    elif len(messages) != len(final_sequence): # Log if changes were made (even without full debug)
        logger.info(f"Repair changed message count from {len(messages)} to {len(final_sequence)}")

    return final_sequence
