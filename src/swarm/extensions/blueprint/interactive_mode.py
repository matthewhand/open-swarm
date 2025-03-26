"""
Interactive mode logic for blueprint extensions.
"""

import logging
from typing import List, Dict

# Import the standalone output function
from .output_utils import pretty_print_response
# Assuming spinner is managed by the blueprint instance passed in
# from .spinner import Spinner # Not needed directly here

logger = logging.getLogger(__name__)

def run_interactive_mode(blueprint, stream: bool = False) -> None:
    """
    Run the interactive mode for a blueprint instance.

    This function implements the interactive loop where the user is prompted for input,
    and responses are generated and printed using the blueprint instance's methods.
    """
    logger.debug("Starting interactive mode.")
    if not blueprint.starting_agent or not blueprint.swarm:
        logger.error("Starting agent or Swarm not initialized.")
        raise ValueError("Starting agent and Swarm must be initialized.")
    print("Blueprint Interactive Mode 🐝")
    messages: List[Dict[str, str]] = []
    first_input = True
    message_count = 0
    while True:
        # Use the blueprint's spinner instance if it exists
        spinner = getattr(blueprint, 'spinner', None)
        if spinner:
            spinner.stop()

        user_input = input(blueprint.prompt).strip()
        if user_input.lower() in {"exit", "quit", "/quit"}:
            print("Exiting interactive mode.")
            break
        if first_input:
            blueprint.context_variables["user_goal"] = user_input
            first_input = False
        messages.append({"role": "user", "content": user_input})
        message_count += 1

        # run_with_context should handle its own spinner start/stop now
        result = blueprint.run_with_context(messages, blueprint.context_variables)
        swarm_response = result["response"]

        # Determine response messages
        response_messages = []
        if hasattr(swarm_response, 'messages'):
            response_messages = swarm_response.messages
        elif isinstance(swarm_response, dict) and 'messages' in swarm_response:
            response_messages = swarm_response.get('messages', [])

        # Process output
        if stream:
            # Assuming _process_and_print_streaming_response_async exists on blueprint
            # This might also need updating if it relies on the old print method
            try:
                import asyncio
                asyncio.run(blueprint._process_and_print_streaming_response_async(swarm_response))
            except AttributeError:
                 logger.error("Blueprint instance missing '_process_and_print_streaming_response_async' method for streaming.")
                 print("[Error: Streaming output failed]")
            except Exception as e:
                 logger.error(f"Error during streaming output: {e}", exc_info=True)
                 print("[Error during streaming output]")

        else:
            # Use the imported pretty_print_response function
            pretty_print_response(
                response_messages,
                use_markdown=getattr(blueprint, 'use_markdown', False),
                spinner=spinner # Pass the spinner instance
            )

        # Extend history and handle post-response logic
        messages.extend(response_messages)

        # Check for goal update logic
        if getattr(blueprint, 'update_user_goal', False) and \
           (message_count - getattr(blueprint, 'last_goal_update_count', 0)) >= \
           getattr(blueprint, 'update_user_goal_frequency', 5):
            # Assume _update_user_goal is an async method on blueprint
            try:
                import asyncio
                asyncio.run(blueprint._update_user_goal_async(messages))
                blueprint.last_goal_update_count = message_count
            except AttributeError:
                logger.warning("Blueprint instance missing '_update_user_goal_async' method.")
            except Exception as e:
                logger.error(f"Error updating user goal: {e}", exc_info=True)


        # Check for auto-complete logic
        if getattr(blueprint, 'auto_complete_task', False):
            # Assume _auto_complete_task is an async method on blueprint
            try:
                import asyncio
                asyncio.run(blueprint._auto_complete_task_async(messages, stream))
            except AttributeError:
                 logger.warning("Blueprint instance missing '_auto_complete_task_async' method.")
            except Exception as e:
                 logger.error(f"Error during auto-complete task: {e}", exc_info=True)

