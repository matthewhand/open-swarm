"""
Utility functions for Swarm views.
"""
import json
import uuid
import time
import os
import redis
import logging
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

# Project-specific imports
from swarm.models import ChatConversation, ChatMessage
from swarm.extensions.blueprint import discover_blueprints
from swarm.extensions.blueprint.blueprint_base import BlueprintBase
from swarm.extensions.config.config_loader import load_server_config, load_llm_config
from swarm.utils.logger_setup import setup_logger
from swarm.utils.redact import redact_sensitive_data
from swarm.utils.general_utils import extract_chat_id
from swarm.extensions.blueprint.blueprint_utils import filter_blueprints
from swarm.settings import BASE_DIR, BLUEPRINTS_DIR # Import BLUEPRINTS_DIR

logger = setup_logger(__name__)

# --- Configuration Loading ---
CONFIG_PATH = Path(settings.BASE_DIR) / 'swarm_config.json'
config = {}
llm_config = {}
llm_model = "default"
llm_provider = "unknown"

def load_configs():
    """Load main and LLM configurations."""
    global config, llm_config, llm_model, llm_provider
    try:
        config = load_server_config(str(CONFIG_PATH))
        logger.info(f"Server config loaded from {CONFIG_PATH}")
    except FileNotFoundError:
        logger.warning(f"Configuration file not found at {CONFIG_PATH}. Using defaults.")
        config = {} # Use empty dict or default structure if needed
    except ValueError as e:
        logger.error(f"Error loading server config: {e}. Using defaults.")
        config = {}
    except Exception as e:
        logger.critical(f"Unexpected error loading server config: {e}", exc_info=True)
        config = {} # Critical error, use empty config

    try:
        llm_config = load_llm_config(config) # Load default LLM config
        llm_model = llm_config.get("model", "default")
        llm_provider = llm_config.get("provider", "unknown")
        logger.info(f"Default LLM config loaded: Provider={llm_provider}, Model={llm_model}")
    except ValueError as e:
        logger.error(f"Failed to load default LLM configuration: {e}. LLM features may fail.")
        llm_config = {} # Ensure llm_config is a dict even on error
        llm_model = "error"
        llm_provider = "error"
    except Exception as e:
        logger.critical(f"Unexpected error loading LLM config: {e}", exc_info=True)
        llm_config = {}
        llm_model = "error"
        llm_provider = "error"

load_configs() # Load configs when module is imported

# --- Blueprint Discovery ---
blueprints_metadata = {}
def discover_and_load_blueprints():
    """Discover blueprints from the configured directory."""
    global blueprints_metadata
    try:
        # Ensure BLUEPRINTS_DIR is a Path object
        bp_dir_path = Path(BLUEPRINTS_DIR) if isinstance(BLUEPRINTS_DIR, str) else BLUEPRINTS_DIR
        if not bp_dir_path.is_absolute():
            bp_dir_path = Path(settings.BASE_DIR).parent / bp_dir_path # Assuming relative to project root
        logger.info(f"Discovering blueprints in: {bp_dir_path}")
        discovered = discover_blueprints(directories=[str(bp_dir_path)])
        blueprints_metadata = discovered
        loaded_names = list(blueprints_metadata.keys())
        logger.info(f"Discovered blueprints: {loaded_names if loaded_names else 'None'}")
    except FileNotFoundError:
         logger.warning(f"Blueprints directory '{BLUEPRINTS_DIR}' not found. No blueprints discovered dynamically.")
         blueprints_metadata = {}
    except Exception as e:
        logger.error(f"Failed during blueprint discovery: {e}", exc_info=True)
        blueprints_metadata = {}

discover_and_load_blueprints() # Discover blueprints when module is imported

# --- Redis Client Initialization ---
REDIS_AVAILABLE = bool(os.getenv("STATEFUL_CHAT_ID_PATH")) and hasattr(settings, 'REDIS_HOST') and hasattr(settings, 'REDIS_PORT')
redis_client = None
if REDIS_AVAILABLE:
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
        redis_client.ping()
        logger.info(f"Redis connection successful ({settings.REDIS_HOST}:{settings.REDIS_PORT}).")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Stateful chat history via Redis is disabled.")
        REDIS_AVAILABLE = False
else:
    logger.info("Redis configuration not found or STATEFUL_CHAT_ID_PATH not set. Stateful chat history via Redis is disabled.")

# --- Helper Functions ---

def serialize_swarm_response(response: Any, model_name: str, context_variables: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize a blueprint response into an OpenAI-compatible chat completion format."""
    logger.debug(f"Serializing Swarm response, type: {type(response)}, model: {model_name}")

    # Determine messages from response
    if hasattr(response, 'messages') and isinstance(response.messages, list):
        messages = response.messages
    elif isinstance(response, dict) and isinstance(response.get("messages"), list):
        messages = response.get("messages", [])
    elif isinstance(response, str):
        logger.warning(f"Received raw string response, wrapping as assistant message: {response[:100]}...")
        messages = [{"role": "assistant", "content": response}]
    else:
        logger.error(f"Unexpected response type for serialization: {type(response)}. Returning empty response.")
        messages = []

    # Create choices array based on assistant messages with content
    choices = []
    for i, msg in enumerate(messages):
        if isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("content") is not None:
            choice = {
                "index": len(choices),
                "message": {
                    "role": "assistant",
                    "content": msg["content"]
                },
                "finish_reason": "stop" # Assume stop for non-streaming
            }
            # Include tool_calls if present in the original message
            if msg.get("tool_calls") is not None:
                 choice["message"]["tool_calls"] = msg["tool_calls"]
                 choice["finish_reason"] = "tool_calls" # Adjust finish reason if tools are called

            choices.append(choice)
            logger.debug(f"Added choice {len(choices)-1}: role={choice['message']['role']}, finish={choice['finish_reason']}")

    if not choices and messages:
         # Fallback if no assistant message with content, maybe use last message?
         logger.warning("No assistant messages with content found for 'choices'. Using last message if possible.")
         # This part might need refinement based on expected behavior for tool-only responses

    # Estimate token usage (basic approximation)
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    # Need access to the *input* messages for prompt_tokens, which aren't passed here.
    # This usage calculation will be inaccurate without the original prompt.
    for msg in messages: # Calculating based on response messages only
        if isinstance(msg, dict):
            content_tokens = len(str(msg.get("content", "")).split())
            if msg.get("role") == "assistant":
                completion_tokens += content_tokens
            total_tokens += content_tokens
            if msg.get("tool_calls"): # Add rough estimate for tool call overhead
                total_tokens += len(json.dumps(msg["tool_calls"])) // 4

    logger.warning("Token usage calculation is approximate and based only on response messages.")

    # Basic serialization structure
    serialized_response = {
        "id": f"swarm-chat-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": choices,
        "usage": {
            "prompt_tokens": prompt_tokens, # Inaccurate without input messages
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens # Inaccurate
        },
        # Optionally include context and full response for debugging/state
        # "context_variables": context_variables,
        # "full_response": response # Might contain non-serializable objects
    }

    logger.debug(f"Serialized response: id={serialized_response['id']}, choices={len(choices)}")
    return serialized_response

def parse_chat_request(request: Any) -> Any:
    """Parse incoming chat completion request body into components."""
    try:
        body = json.loads(request.body)
        model = body.get("model", "default") # Default to 'default' if model not specified
        messages = body.get("messages", [])

        # Basic validation
        if not isinstance(messages, list) or not messages:
             # Try extracting single message if 'messages' is invalid/empty
             if "message" in body:
                  single_msg = body["message"]
                  if isinstance(single_msg, str): messages = [{"role": "user", "content": single_msg}]
                  elif isinstance(single_msg, dict) and "content" in single_msg:
                       if "role" not in single_msg: single_msg["role"] = "user"
                       messages = [single_msg]
                  else:
                       return Response({"error": "'message' field is invalid."}, status=status.HTTP_400_BAD_REQUEST)
             else:
                  return Response({"error": "'messages' field is required and must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure all messages have a role (default to user if missing)
        for msg in messages:
            if not isinstance(msg, dict) or "content" not in msg:
                 # Allow tool calls without content
                 if not (isinstance(msg, dict) and msg.get("role") == "tool" and msg.get("tool_call_id")):
                     logger.error(f"Invalid message format found: {msg}")
                     return Response({"error": f"Invalid message format: {msg}"}, status=status.HTTP_400_BAD_REQUEST)
            if "role" not in msg:
                msg["role"] = "user"

        context_variables = body.get("context_variables", {})
        if not isinstance(context_variables, dict):
             logger.warning("Invalid 'context_variables' format, using empty dict.")
             context_variables = {}

        conversation_id = extract_chat_id(body) or str(uuid.uuid4()) # Generate if not found/extracted

        # Extract last tool_call_id for potential context filtering (optional)
        tool_call_id = None
        if messages and isinstance(messages[-1], dict) and messages[-1].get("role") == "tool":
             tool_call_id = messages[-1].get("tool_call_id")

        logger.debug(f"Parsed request: model={model}, messages_count={len(messages)}, context_keys={list(context_variables.keys())}, conv_id={conversation_id}, tool_id={tool_call_id}")
        return (body, model, messages, context_variables, conversation_id, tool_call_id)

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received.")
        return Response({"error": "Invalid JSON payload."}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
         logger.error(f"Error parsing request: {e}", exc_info=True)
         return Response({"error": "Failed to parse request."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_blueprint_instance(model: str, context_vars: dict) -> Any:
    """Instantiate a blueprint instance based on the requested model."""
    logger.debug(f"Attempting to get blueprint instance for model: {model}")
    # Reload configs and discover blueprints on each request? Or rely on initial load?
    # Let's rely on initial load for now, assuming blueprints don't change often.
    # discover_and_load_blueprints() # Uncomment if dynamic reload is needed

    blueprint_meta = blueprints_metadata.get(model)
    if not blueprint_meta:
        # Check if it's an LLM passthrough defined in config
        llm_profile = config.get("llm", {}).get(model)
        if llm_profile and llm_profile.get("passthrough"):
             logger.warning(f"Model '{model}' is an LLM passthrough, not a blueprint. Returning None.")
             # This scenario should ideally be handled before calling get_blueprint_instance
             # Returning None might cause issues downstream. Consider raising an error
             # or having the caller handle LLM passthrough separately.
             # For now, returning None as a signal.
             return None # Signal it's not a blueprint
        else:
             logger.error(f"Model '{model}' not found in discovered blueprints or LLM config.")
             return Response({"error": f"Model '{model}' not found."}, status=status.HTTP_404_NOT_FOUND)

    blueprint_class = blueprint_meta.get("blueprint_class")
    if not blueprint_class or not issubclass(blueprint_class, BlueprintBase):
        logger.error(f"Blueprint class for model '{model}' is invalid or not found.")
        return Response({"error": f"Blueprint class for model '{model}' is invalid."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        # Pass the initially loaded global 'config' to the blueprint instance
        blueprint_instance = blueprint_class(config=config, debug=settings.DEBUG)
        logger.info(f"Successfully instantiated blueprint: {model}")
        # Optionally set active agent based on context, if blueprint supports it
        # active_agent_name = context_vars.get("active_agent_name")
        # if active_agent_name and hasattr(blueprint_instance, 'set_active_agent'):
        #     try:
        #         blueprint_instance.set_active_agent(active_agent_name)
        #     except ValueError as e:
        #         logger.warning(f"Could not set active agent '{active_agent_name}': {e}")
        return blueprint_instance
    except Exception as e:
        logger.error(f"Error initializing blueprint '{model}': {e}", exc_info=True)
        return Response({"error": f"Error initializing blueprint: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def load_conversation_history(conversation_id: Optional[str], current_messages: List[dict], tool_call_id: Optional[str] = None) -> List[dict]:
    """Load past messages for a conversation from Redis or database, combined with current."""
    if not conversation_id:
        logger.debug("No conversation_id provided, returning only current messages.")
        return current_messages # Return only the messages from the current request

    past_messages = []
    # Try Redis first if available
    if REDIS_AVAILABLE and redis_client:
        try:
            history_raw = redis_client.lrange(conversation_id, 0, -1) # Get all items in list
            if history_raw:
                # Redis stores list items as strings, parse each JSON string
                past_messages = [json.loads(msg_str) for msg_str in history_raw]
                logger.debug(f"Retrieved {len(past_messages)} messages from Redis list for conversation: {conversation_id}")
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error retrieving history for {conversation_id}: {e}", exc_info=True)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from Redis for {conversation_id}: {e}. History may be corrupted.")
            # Potentially clear corrupted Redis key?
            # redis_client.delete(conversation_id)
        except Exception as e:
            logger.error(f"Unexpected error retrieving from Redis for {conversation_id}: {e}", exc_info=True)

    # Fallback to Database if Redis fails or history is empty
    if not past_messages:
        try:
            conversation = ChatConversation.objects.filter(conversation_id=conversation_id).first()
            if conversation:
                # Query messages related to the conversation
                query = conversation.messages.all().order_by("timestamp")
                # Convert DB messages to the expected dict format
                past_messages = [
                    {"role": msg.sender, "content": msg.content, "tool_calls": json.loads(msg.tool_calls) if msg.tool_calls else None}
                    for msg in query
                ]
                logger.debug(f"Retrieved {len(past_messages)} messages from DB for conversation: {conversation_id}")
            else:
                logger.debug(f"No existing conversation found in DB for ID: {conversation_id}")
                past_messages = [] # Ensure it's an empty list if no conversation found
        except Exception as e:
            logger.error(f"Error retrieving conversation history from DB for {conversation_id}: {e}", exc_info=True)
            past_messages = [] # Ensure empty list on error

    # Combine history with current request messages
    # Ensure roles are correct ('user' for human, 'assistant'/'tool' for AI/tools)
    # Filter out potential duplicates if necessary (e.g., if client resends last user message)
    combined_messages = past_messages + current_messages
    logger.debug(f"Combined history: {len(past_messages)} past + {len(current_messages)} current = {len(combined_messages)} total messages for {conversation_id}")
    return combined_messages


def store_conversation_history(conversation_id: str, full_history: List[dict], response_obj: Optional[Any] = None):
    """Store conversation history (including latest response) in DB and/or Redis."""
    if not conversation_id:
        logger.error("Cannot store history: conversation_id is missing.")
        return False

    # Ensure response messages are included in the history to be stored
    history_to_store = list(full_history) # Make a copy
    if response_obj:
        response_messages = []
        if hasattr(response_obj, 'messages') and isinstance(response_obj.messages, list):
             response_messages = response_obj.messages
        elif isinstance(response_obj, dict) and isinstance(response_obj.get('messages'), list):
             response_messages = response_obj.get('messages', [])

        # Add only messages not already in full_history (prevent duplicates if run_conversation includes input)
        last_stored_content = json.dumps(history_to_store[-1]) if history_to_store else None
        for msg in response_messages:
             if json.dumps(msg) != last_stored_content:
                  history_to_store.append(msg)


    # --- Store in Database ---
    try:
        # Use update_or_create for conversation to handle creation/retrieval atomically
        conversation, created = ChatConversation.objects.update_or_create(
            conversation_id=conversation_id,
            defaults={'user': None} # Add user association if available (e.g., from request.user)
        )
        if created:
            logger.debug(f"Created new ChatConversation in DB: {conversation_id}")

        # Efficiently store only the messages *added* in this turn (response messages)
        # Assume `full_history` contains the prompt messages, and `response_messages` contains the response
        messages_to_add_to_db = []
        if response_obj:
            response_msgs_from_obj = getattr(response_obj, 'messages', []) if hasattr(response_obj, 'messages') else response_obj.get('messages', []) if isinstance(response_obj, dict) else []
            for msg in response_msgs_from_obj:
                 if isinstance(msg, dict):
                     # Basic validation
                     role = msg.get("role")
                     content = msg.get("content")
                     tool_calls = msg.get("tool_calls")
                     if role and (content is not None or tool_calls is not None):
                          messages_to_add_to_db.append(ChatMessage(
                              conversation=conversation,
                              sender=role,
                              content=content,
                              # Store tool_calls as JSON string
                              tool_calls=json.dumps(tool_calls) if tool_calls else None
                          ))

        if messages_to_add_to_db:
             ChatMessage.objects.bulk_create(messages_to_add_to_db)
             logger.debug(f"Stored {len(messages_to_add_to_db)} new messages in DB for conversation {conversation_id}")
        else:
             logger.debug(f"No new response messages to store in DB for conversation {conversation_id}")

    except Exception as e:
        logger.error(f"Error storing conversation history to DB for {conversation_id}: {e}", exc_info=True)
        # Continue to Redis even if DB fails? Or return False? Let's continue for now.

    # --- Store full history in Redis List ---
    if REDIS_AVAILABLE and redis_client:
        try:
            # Use a Redis list (LPUSH/LTRIM or RPUSH/LTRIM for potentially capped history)
            # For simplicity, let's replace the entire history for now.
            # Delete existing list and push all new items. Use pipeline for atomicity.
            pipe = redis_client.pipeline()
            pipe.delete(conversation_id)
            # Push each message as a separate JSON string onto the list
            for msg_dict in history_to_store:
                 pipe.rpush(conversation_id, json.dumps(msg_dict))
            # Optionally cap the list size
            # max_redis_history = 100 # Example cap
            # pipe.ltrim(conversation_id, -max_redis_history, -1)
            pipe.execute()
            logger.debug(f"Stored {len(history_to_store)} messages in Redis list for conversation {conversation_id}")
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error storing history list for {conversation_id}: {e}", exc_info=True)
            return False # Indicate failure if Redis write fails
        except Exception as e:
            logger.error(f"Unexpected error storing to Redis for {conversation_id}: {e}", exc_info=True)
            return False

    return True


async def run_conversation(blueprint_instance: Any, messages_extended: List[dict], context_vars: dict) -> Tuple[Any, dict]:
    """Run a conversation turn with a blueprint instance asynchronously."""
    if not isinstance(blueprint_instance, BlueprintBase):
         # Handle LLM passthrough case if needed, or raise error
         # For now, assume it must be a BlueprintBase instance
         logger.error("run_conversation called with non-blueprint instance.")
         raise TypeError("run_conversation expects a BlueprintBase instance.")

    try:
        # Directly await the async method
        result_dict = await blueprint_instance.run_with_context_async(messages_extended, context_vars)

        response_obj = result_dict.get("response")
        updated_context = result_dict.get("context_variables", context_vars) # Fallback to original context

        if response_obj is None:
             logger.error("Blueprint run returned None in response object.")
             # Create a default error response
             response_obj = {"messages": [{"role": "assistant", "content": "Error: Blueprint failed to return a response."}]}

        return response_obj, updated_context
    except Exception as e:
         logger.error(f"Exception during blueprint run: {e}", exc_info=True)
         # Return an error structure
         error_response = {"messages": [{"role": "assistant", "content": f"Error processing request: {e}"}]}
         return error_response, context_vars # Return original context on error
