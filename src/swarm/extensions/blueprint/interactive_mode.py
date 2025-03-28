"""
Interactive mode logic for blueprint extensions.
"""

import logging
from typing import List, Dict, Any # Added Any

# Import the standalone output function
from .output_utils import pretty_print_response

logger = logging.getLogger(__name__)

def run_interactive_mode(blueprint, stream: bool = False) -> None:
    """
    Run the interactive mode for a blueprint instance.

    This function implements the interactive loop where the user is
prompted for input,
    and responses are generated and printed using the blueprint inst
ance's methods.
    """
    logger.debug("Starting interactive mode.")
    if not blueprint.starting_agent:
        logger.error("Starting agent or Swarm not initialized.")
        # --- FIX: Terminate string literal correctly ---
        raise ValueError("Starting agent and Swarm must be initialized.")
        # --- End FIX ---

    print("Blueprint Interactive Mode 🐝")
    messages: List[Dict[str, Any]] = []
    first_input = True
    message_count = 0
    while True:
        spinner = getattr(blueprint, 'spinner', None)
        if spinner: spinner.stop()

        try:
             user_input = input(blueprint.prompt).strip()
        except (EOFError, KeyboardInterrupt):
             print("\nExiting interactive mode.")
             break

        if user_input.lower() in {"exit", "quit", "/quit"}:
            print("Exiting interactive mode.")
            break
        if first_input:
            blueprint.context_variables["user_goal"] = user_input
            first_input = False
        messages.append({"role": "user", "content": user_input})
        message_count += 1

        try:
             result = blueprint.run_with_context(messages, blueprint.context_variables)
             swarm_response = result.get("response")
             blueprint.context_variables = result.get("context_variables", blueprint.context_variables)

             response_messages_objects = []
             if hasattr(swarm_response, 'messages'):
                 response_messages_objects = swarm_response.messages
             elif isinstance(swarm_response, dict) and 'messages' in swarm_response:
                  raw_msgs = swarm_response.get('messages', [])
                  if raw_msgs and not isinstance(raw_msgs[0], dict):
                       try: response_messages_objects = raw_msgs
                       except Exception: logger.error("Failed to process messages from dict response."); response_messages_objects = []
                  else: response_messages_objects = raw_msgs

             response_messages_dicts = []
             if response_messages_objects:
                 try:
                     response_messages_dicts = [
                         msg.model_dump(exclude_none=True) if hasattr(msg, 'model_dump') else msg
                         for msg in response_messages_objects
                     ]
                 except Exception as e:
                      logger.error(f"Failed to dump response messages to dict: {e}")
                      response_messages_dicts = [{"role": "system", "content": "[Error displaying response]"}]

             if stream:
                 logger.warning("Streaming not fully supported in this interactive mode version.")
                 pretty_print_response(messages=response_messages_dicts, use_markdown=getattr(blueprint, 'use_markdown', False), spinner=spinner)
             else:
                 pretty_print_response(messages=response_messages_dicts, use_markdown=getattr(blueprint, 'use_markdown', False), spinner=spinner)

             messages.extend(response_messages_dicts)

             if getattr(blueprint, 'update_user_goal', False) and \
                (message_count - getattr(blueprint, 'last_goal_update_count', 0)) >= \
                getattr(blueprint, 'update_user_goal_frequency', 5):
                 try:
                     import asyncio
                     asyncio.run(blueprint._update_user_goal_async(messages))
                     blueprint.last_goal_update_count = message_count
                 except AttributeError: logger.warning("Blueprint missing '_update_user_goal_async'.")
                 except Exception as e: logger.error(f"Error updating goal: {e}", exc_info=True)

             if getattr(blueprint, 'auto_complete_task', False):
                  logger.warning("Auto-complete task not implemented in this interactive loop version.")

        except Exception as e:
             logger.error(f"Error during interactive loop turn: {e}", exc_info=True)
             print(f"\n[An error occurred: {e}]")

