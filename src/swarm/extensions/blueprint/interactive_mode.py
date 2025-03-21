"""
Interactive mode logic for blueprint extensions.
"""

import logging
from typing import List, Dict

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
        blueprint.spinner.stop()
        user_input = input(blueprint.prompt).strip()
        if user_input.lower() in {"exit", "quit", "/quit"}:
            print("Exiting interactive mode.")
            break
        if first_input:
            blueprint.context_variables["user_goal"] = user_input
            first_input = False
        messages.append({"role": "user", "content": user_input})
        message_count += 1
        result = blueprint.run_with_context(messages, blueprint.context_variables)
        swarm_response = result["response"]
        response_messages = (
            swarm_response["messages"]
            if isinstance(swarm_response, dict)
            else swarm_response.messages
        )
        if stream:
            blueprint._process_and_print_streaming_response(swarm_response)
        else:
            blueprint._pretty_print_response(response_messages)
        messages.extend(response_messages)
        if blueprint.update_user_goal and (message_count - blueprint.last_goal_update_count) >= blueprint.update_user_goal_frequency:
            blueprint._update_user_goal(messages)
            blueprint.last_goal_update_count = message_count
        if blueprint.auto_complete_task:
            blueprint._auto_complete_task(messages, stream)