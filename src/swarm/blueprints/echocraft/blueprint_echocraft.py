
# --- Content for src/swarm/blueprints/echocraft/blueprint_echocraft.py ---
import logging
from typing import List, Dict, Any, AsyncGenerator
import uuid # Import uuid to generate IDs
import time # Import time for timestamp

from swarm.extensions.blueprint.blueprint_base import BlueprintBase

logger = logging.getLogger(__name__)

class EchoCraftBlueprint(BlueprintBase):
    """
    A simple blueprint that echoes the last user message.
    Used for testing and demonstrating basic blueprint structure.
    """

    # No specific __init__ needed beyond the base class unless adding more params
    # def __init__(self, blueprint_id: str, **kwargs):
    #     super().__init__(blueprint_id=blueprint_id, **kwargs)
    #     logger.info(f"EchoCraftBlueprint '{self.blueprint_id}' initialized.")

    async def run(self, messages: List[Dict[str, Any]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Echoes the content of the last message with role 'user'.
        Yields a final message in OpenAI ChatCompletion format.
        """
        logger.info(f"EchoCraftBlueprint run called with {len(messages)} messages.")

        last_user_message_content = "No user message found."
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message_content = msg.get("content", "(empty content)")
                logger.debug(f"Found last user message: {last_user_message_content}")
                break

        echo_content = f"Echo: {last_user_message_content}"
        logger.info(f"EchoCraftBlueprint yielding: {echo_content}")

        # --- Format the final output as an OpenAI ChatCompletion object ---
        completion_id = f"chatcmpl-echo-{uuid.uuid4()}"
        created_timestamp = int(time.time())

        final_message_chunk = {
            "id": completion_id,
            "object": "chat.completion",
            "created": created_timestamp,
            "model": self.llm_profile_name, # Use profile name as model identifier
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": echo_content,
                    },
                    "finish_reason": "stop",
                    "logprobs": None, # Add null logprobs if needed
                }
            ],
            # Add usage stats if desired/possible
            # "usage": {
            #     "prompt_tokens": 0,
            #     "completion_tokens": 0,
            #     "total_tokens": 0
            # }
        }
        yield final_message_chunk
        # --- End formatting change ---

        logger.info("EchoCraftBlueprint run finished.")

