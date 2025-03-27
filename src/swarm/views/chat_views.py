"""
Chat-related views for Open Swarm MCP Core.
"""
import asyncio
import logging
import json
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from swarm.auth import EnvOrTokenAuthentication
from swarm.utils.logger_setup import setup_logger
from swarm.views import utils as view_utils
from swarm.extensions.config.config_loader import config
from swarm.settings import Settings

logger = setup_logger(__name__)

# Removed _run_async_in_sync helper

@api_view(['POST'])
@csrf_exempt
@authentication_classes([EnvOrTokenAuthentication])
@permission_classes([IsAuthenticated])
def chat_completions(request): # Sync view
    """Handle chat completion requests via POST."""
    if request.method != "POST":
        return Response({"error": "Method not allowed. Use POST."}, status=405)
    logger.info(f"Authenticated User: {request.user}")

    parse_result = view_utils.parse_chat_request(request)
    if isinstance(parse_result, Response): return parse_result

    body, model, messages, context_vars, conversation_id, tool_call_id = parse_result
    model_type = "llm" if model in config.get('llm', {}) and config.get('llm', {}).get(model, {}).get("passthrough") else "blueprint"
    logger.info(f"Identified model type: {model_type} for model: {model}")

    if model_type == "llm":
         return Response({"error": f"LLM passthrough for model '{model}' not implemented."}, status=501)

    try:
        blueprint_instance = view_utils.get_blueprint_instance(model, context_vars)
        messages_extended = view_utils.load_conversation_history(conversation_id, messages, tool_call_id)

        # Try running the async function using asyncio.run()
        # This might fail in test environments with existing loops.
        try:
            logger.debug("Attempting asyncio.run(run_conversation)...")
            response_obj, updated_context = asyncio.run(
                view_utils.run_conversation(blueprint_instance, messages_extended, context_vars)
            )
            logger.debug("asyncio.run(run_conversation) completed.")
        except RuntimeError as e:
             # Catch potential nested loop errors specifically from asyncio.run()
             logger.error(f"Asyncio run error: {e}", exc_info=True)
             # Return a 500 error, as the async call couldn't be completed
             return Response({"error": f"Server execution error: {str(e)}"}, status=500)


        serialized = view_utils.serialize_swarm_response(response_obj, model, updated_context)

        if conversation_id:
            serialized["conversation_id"] = conversation_id
            view_utils.store_conversation_history(conversation_id, messages_extended, response_obj)

        return Response(serialized, status=200)

    except FileNotFoundError as e:
         logger.warning(f"Blueprint not found for model '{model}': {e}")
         return Response({"error": f"Blueprint not found: {model}"}, status=404)
    # Catch other exceptions, including the potential RuntimeError from above
    except Exception as e:
        logger.error(f"Error during execution for model '{model}': {e}", exc_info=True)
        error_msg = str(e) if Settings().debug else "An internal error occurred."
        return Response({"error": f"Error during execution: {error_msg}"}, status=500)

