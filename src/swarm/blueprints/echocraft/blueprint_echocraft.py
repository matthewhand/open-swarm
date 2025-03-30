import logging
from typing import Dict, List, Any, AsyncGenerator
# Correct import path for BlueprintBase
from swarm.extensions.blueprint.blueprint_base import BlueprintBase

logger = logging.getLogger(__name__)

class EchoCraftBlueprint(BlueprintBase):
    """
    A simple blueprint that echoes the last user message.
    """
    metadata = {
        "name": "EchoCraft",
        "description": "Echoes the last user message.",
        "author": "SwarmTeam",
        "version": "1.0",
        # Example: Specify a default LLM profile if desired
        # "llm_profile": "default"
    }

    # *** Make run async and use yield ***
    async def run(self, messages: List[Dict[str, str]]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Finds the last user message and yields it back with an 'Echo: ' prefix.
        """
        logger.info(f"EchoCraftBlueprint run called with {len(messages)} messages.")
        last_user_message = "No user message found."
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                logger.debug(f"Found last user message: {last_user_message}")
                break

        response_content = f"Echo: {last_user_message}"
        logger.info(f"EchoCraftBlueprint yielding: {response_content}")

        # Yield the final response in the expected format
        yield {
            "messages": [
                {"role": "assistant", "content": response_content}
            ]
        }
        logger.info("EchoCraftBlueprint run finished.")

