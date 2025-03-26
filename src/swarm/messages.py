"""
Message handling utilities for the Swarm framework.
Defines the ChatMessage structure.
"""

import json
import logging
from types import SimpleNamespace
from typing import Optional, List, Dict, Any, Union

# Import the specific Pydantic model used for tool calls
from .types import ChatCompletionMessageToolCall

# Configure module-level logging
logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG) # Uncomment for detailed message logging
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s:%(lineno)d - %(message)s")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


class ChatMessage(SimpleNamespace):
    """
    Represents a chat message within the Swarm framework, aiming for compatibility
    with OpenAI's chat completion message structure while allowing custom fields.

    Attributes:
        role (str): The role of the message sender (e.g., "system", "user", "assistant", "tool").
        content (Optional[str]): The text content of the message. Can be None for assistant messages
                                 requesting tool calls without initial text.
        sender (str): Custom field identifying the specific agent or source (not sent to LLM API).
        function_call (Optional[dict]): Deprecated field for legacy function calls.
        tool_calls (Optional[List[ChatCompletionMessageToolCall]]): A list of tool calls requested
                                                                    by the assistant.
        tool_call_id (Optional[str]): Identifier for a tool response message, linking it to a specific
                                     tool_call requested by the assistant.
        name (Optional[str]): The name of the tool that was called (used in 'tool' role messages).
    """

    def __init__(self, **kwargs):
        """
        Initialize a ChatMessage instance.

        Args:
            **kwargs: Arbitrary keyword arguments mapping to message attributes.
                      Defaults are provided for common fields.
        """
        # Define default values for standard message attributes
        defaults = {
            "role": "assistant", # Default role
            "content": None, # Default content to None (as per OpenAI spec for tool calls)
            "sender": "assistant", # Default custom sender
            "function_call": None, # Deprecated field
            "tool_calls": None, # For assistant requests
            "tool_call_id": None, # For tool responses
            "name": None # For tool responses (function name)
        }
        # Merge provided kwargs with defaults
        merged_attrs = defaults | kwargs
        super().__init__(**merged_attrs)

        # --- Validation and Type Conversion for tool_calls ---
        # Ensure tool_calls, if present, is a list
        if self.tool_calls is not None and not isinstance(self.tool_calls, list):
            logger.warning(f"ChatMessage 'tool_calls' received non-list type ({type(self.tool_calls)}) for sender '{self.sender}'. Resetting to None.")
            self.tool_calls = None
        elif isinstance(self.tool_calls, list):
            # Convert dictionary items in the list to ChatCompletionMessageToolCall objects
            validated_tool_calls = []
            for i, tc in enumerate(self.tool_calls):
                if isinstance(tc, ChatCompletionMessageToolCall):
                    validated_tool_calls.append(tc)
                elif isinstance(tc, dict):
                    try:
                        # Attempt to instantiate the Pydantic model
                        validated_tool_calls.append(ChatCompletionMessageToolCall(**tc))
                    except Exception as e: # Catch potential validation errors from Pydantic
                        logger.warning(f"Failed to convert dict to ChatCompletionMessageToolCall at index {i} for sender '{self.sender}': {e}. Skipping this tool call.")
                        logger.debug(f"Invalid tool call dict: {tc}")
                else:
                    logger.warning(f"Invalid item type in 'tool_calls' list at index {i} ({type(tc)}) for sender '{self.sender}'. Skipping.")
            self.tool_calls = validated_tool_calls if validated_tool_calls else None # Set back validated list or None if empty/all invalid
            if self.tool_calls:
                 logger.debug(f"Validated {len(self.tool_calls)} tool calls for ChatMessage (sender: '{self.sender}')")


    def model_dump(self) -> Dict[str, Any]:
         """
         Serialize the message attributes relevant for the OpenAI API into a dictionary.
         Excludes custom fields like 'sender'. Handles optional fields correctly.
         """
         # Start with required 'role'
         d: Dict[str, Any] = {"role": self.role}

         # Include 'content' only if it's not None
         # OpenAI API allows null content for assistant messages with tool_calls
         if self.content is not None:
             d["content"] = self.content

         # Include 'tool_calls' if present and not empty
         if self.tool_calls: # Checks for non-None and non-empty list after validation
             # Ensure each item is dumped correctly using its own model_dump if available
             d["tool_calls"] = [tc.model_dump() if hasattr(tc, 'model_dump') else tc for tc in self.tool_calls]

         # Include 'tool_call_id' if present (for 'tool' role messages)
         if self.tool_call_id is not None:
             d["tool_call_id"] = self.tool_call_id

         # Include 'name' if present (for 'tool' role messages, matches function name)
         if self.name is not None:
              d["name"] = self.name

         # Include deprecated 'function_call' if present
         if self.function_call is not None:
             d["function_call"] = self.function_call

         return d


    def model_dump_json(self) -> str:
        """Serialize the message to a JSON string suitable for the OpenAI API."""
        # Use the model_dump method to get the correct dictionary structure first
        api_dict = self.model_dump()
        # Serialize the dictionary to JSON
        try:
            return json.dumps(api_dict)
        except TypeError as e:
             logger.error(f"Failed to serialize ChatMessage to JSON for sender '{self.sender}': {e}")
             # Fallback: return a basic JSON representation on error
             return json.dumps({"role": self.role, "content": f"[Serialization Error: {e}]"})
