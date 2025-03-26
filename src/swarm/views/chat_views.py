"""
Chat-related views for Open Swarm MCP Core.
"""
import asyncio # Import asyncio
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from swarm.auth import EnvOrTokenAuthentication
from swarm.utils.logger_setup import setup_logger
# Import utils but rename to avoid conflict if this module grows
from swarm.views import utils as view_utils
# from swarm.views.utils import parse_chat_request, serialize_swarm_response, get_blueprint_instance
# from swarm.views.utils import load_conversation_history, store_conversation_history, run_conversation
# from swarm.views.utils import config, llm_config  # Import from utils

logger = setup_logger(__name__)

# Revert to standard sync def
@api_view(['POST'])
@csrf_exempt
@authentication_classes([EnvOrTokenAuthentication])
@permission_classes([IsAuthenticated])
def chat_completions(request): # Mark as sync again
    """Handle chat completion requests via POST."""
    if request.method != "POST":
        return Response({"error": "Method not allowed. Use POST."}, status=405)
    logger.info(f"Authenticated User: {request.user}")

    # Use functions from view_utils
    parse_result = view_utils.parse_chat_request(request)
    if isinstance(parse_result, Response):
        return parse_result

    body, model, messages, context_vars, conversation_id, tool_call_id = parse_result
    # Use llm_config loaded in utils
    model_type = "llm" if model in view_utils.llm_config and view_utils.llm_config[model].get("passthrough") else "blueprint"
    logger.info(f"Identified model type: {model_type} for model: {model}")

    # --- Handle LLM Passthrough directly ---
    if model_type == "llm":
         logger.warning(f"LLM Passthrough requested for model '{model}'. This is not yet fully implemented in this view.")
         # TODO: Implement direct call to Swarm core or LLM client for passthrough
         return Response({"error": f"LLM passthrough for model '{model}' not implemented."}, status=501)

    # --- Handle Blueprint ---
    blueprint_instance = view_utils.get_blueprint_instance(model, context_vars)
    if isinstance(blueprint_instance, Response): # Handle error response from get_blueprint_instance
        return blueprint_instance
    if blueprint_instance is None: # Handle case where get_blueprint_instance signaled non-blueprint
         return Response({"error": f"Model '{model}' is not a loadable blueprint."}, status=404)


    messages_extended = view_utils.load_conversation_history(conversation_id, messages, tool_call_id)

    try:
        # Use asyncio.run() to call the async run_conversation function
        # This blocks the sync view until the async operation completes.
        try:
            response_obj, updated_context = asyncio.run(
                view_utils.run_conversation(blueprint_instance, messages_extended, context_vars)
            )
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                 logger.error("Detected nested asyncio.run call. This can happen in certain test/server setups.")
                 # If already in a loop (e.g., certain test runners or ASGI servers),
                 # you might need a different way to run the async code, like ensure_future
                 # or adapting the server setup. For now, return an error.
                 return Response({"error": "Server configuration error: Nested event loop detected."}, status=500)
            else:
                 raise e # Reraise other RuntimeErrors

        serialized = view_utils.serialize_swarm_response(response_obj, model, updated_context)

        if conversation_id:
            serialized["conversation_id"] = conversation_id
            # Storing history can remain synchronous for now unless it becomes a bottleneck
            view_utils.store_conversation_history(conversation_id, messages_extended, response_obj)

        return Response(serialized, status=200)
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        return Response({"error": f"Error during execution: {str(e)}"}, status=500)
