"""
REST Mode Views for Open Swarm MCP.

This module defines asynchronous views to handle chat completions and model listings,
aligning with OpenAI's Chat Completions API.

Endpoints:
    - POST /v1/chat/completions: Handles chat completion requests.
    - GET /v1/models: Lists available blueprints as models.
    - GET /django_chat/: Lists conversations for the logged-in user.
    - POST /django_chat/start/: Starts a new conversation.
"""
import json
import uuid
import time
import os
import redis
from typing import Any, Dict, List
from pathlib import Path
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse
from django.views.generic import TemplateView
from django.views import View
from django.http import JsonResponse, HttpResponse
from rest_framework.response import Response  # type: ignore
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from swarm.auth import EnvOrTokenAuthentication
from swarm.models import ChatConversation
from swarm.extensions.blueprint import discover_blueprints
from swarm.extensions.config.config_loader import (
    load_server_config,
    load_llm_config,
)
from swarm.utils.logger_setup import setup_logger
from swarm.utils.redact import redact_sensitive_data
from swarm.utils.general_utils import extract_chat_id

# Initialize logger for this module
logger = setup_logger(__name__)
# Initialize Redis if available
REDIS_AVAILABLE = os.getenv("STATEFUL_CHAT_ID_PATH") and settings.DJANGO_DATABASE == "postgres"
redis_client = None

if REDIS_AVAILABLE:
    try:
        redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Redis connection successful.")
    except Exception as e:
        logger.warning(f"⚠️  Redis unavailable, falling back to PostgreSQL: {e}")
        REDIS_AVAILABLE = False

# Load configuration
CONFIG_PATH = Path(settings.BASE_DIR) / "swarm_config.json"
try:
    config = load_server_config(str(CONFIG_PATH))
    redacted_config = redact_sensitive_data(config)  # Redact before logging
    logger.debug(f"Loaded configuration from {CONFIG_PATH}: {redacted_config}")
except Exception as e:
    logger.critical(f"Failed to load configuration from {CONFIG_PATH}: {e}")
    raise e

# Discover blueprints
BLUEPRINTS_DIR = (Path(settings.BASE_DIR) / "blueprints").resolve()
try:
    blueprints_metadata = discover_blueprints([str(BLUEPRINTS_DIR)])
    redacted_blueprints_metadata = redact_sensitive_data(blueprints_metadata)  # Redact before logging
    logger.debug(f"Discovered blueprints meta {redacted_blueprints_metadata}")
except Exception as e:
    logger.error(f"Error discovering blueprints: {e}", exc_info=True)
    raise e

# Inject LLM metadata into blueprints
try:
    llm_config = load_llm_config(config)
    llm_model = llm_config.get("model", "default")
    llm_provider = llm_config.get("provider", "openai")

    for blueprint in blueprints_metadata.values():
        blueprint["openai_model"] = llm_model
        blueprint["llm_provider"] = llm_provider
except ValueError as e:
    logger.critical(f"Failed to load LLM configuration: {e}")
    raise e

def serialize_swarm_response(response: Any, model_name: str, context_variables: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serializes the Swarm response while removing non-serializable objects like functions.
    
    Args:
        response (Any): The response object from the LLM or blueprint.
        model_name (str): The name of the model used.
        context_variables (Dict[str, Any]): Additional context variables maintained across interactions.
    
    Returns:
        Dict[str, Any]: A structured JSON response that includes the full conversation history,
        tool calls, and additional context.
    """
    # Convert to dictionary if response is a Pydantic object
    if hasattr(response, "model_dump"):
        response = response.model_dump()

    messages = response.get("messages", [])

    # Ensure function objects are removed everywhere
    def remove_functions(obj):
        """Recursively remove function objects and other non-serializable types."""
        if isinstance(obj, dict):
            return {k: remove_functions(v) for k, v in obj.items() if not callable(v)}
        elif isinstance(obj, list):
            return [remove_functions(item) for item in obj if not callable(item)]
        elif isinstance(obj, tuple):
            return tuple(remove_functions(item) for item in obj if not callable(item))
        return obj  # Return the object if it's neither a dict nor a list

    # Strip out any functions from agent details
    if "agent" in response:
        response["agent"] = remove_functions(response["agent"])

    # Strip out functions from context variables
    clean_context_variables = remove_functions(context_variables)

    # Remove all function references from response
    clean_response = remove_functions(response)

    formatted_messages = [
        {
            "index": i,
            "message": msg,  # Preserve full raw message, without filtering fields
            "finish_reason": "stop"
        }
        for i, msg in enumerate(messages)
    ]

    return {
        "id": f"swarm-chat-completion-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": formatted_messages,
        "usage": {
            "prompt_tokens": sum(len((msg.get("content") or "").split()) for msg in messages),
            "completion_tokens": sum(len((msg.get("content") or "").split()) for msg in messages if msg.get("role") == "assistant"),
            "total_tokens": len(messages),
        },
        "context_variables": clean_context_variables,  # Ensure no functions in context
        "full_response": clean_response,  # Fully cleaned response
    }

@api_view(['POST'])
@csrf_exempt
@authentication_classes([EnvOrTokenAuthentication])
@permission_classes([IsAuthenticated])
def chat_completions(request):
    if request.method != "POST":
        return Response({"error": "Method not allowed. Use POST."}, status=405)
    
    logger.info(f"Authenticated User: {request.user}")
    logger.info(f"Is Authenticated? {request.user.is_authenticated}")
    
    try:
        body = json.loads(request.body)
        model = body.get("model", "default")
        messages = body.get("messages", [])
        if not messages and "message" in body:
            messages = [body.get("message")]
        messages = [msg if isinstance(msg, dict) else {"content": msg} for msg in messages]
        context_variables = body.get("context_variables", {})
        conversation_id = extract_chat_id(body)
        messages = [msg if isinstance(msg, dict) else {"content": msg} for msg in messages]
        for idx, msg in enumerate(messages):
            if "role" not in msg:
                messages[idx]["role"] = "user"
    
        if not messages:
            return Response({"error": "Messages are required."}, status=400)
    except json.JSONDecodeError:
        return Response({"error": "Invalid JSON payload."}, status=400)
    blueprint_meta = blueprints_metadata.get(model)
    if not blueprint_meta:
        if model == "default":
            from swarm.extensions.blueprint.blueprint_base import BlueprintBase
            class DummyBlueprint(BlueprintBase):
                metadata = {"title": "Dummy Blueprint", "env_vars": []}
                def create_agents(self) -> dict:
                    DummyAgent = type("DummyAgent", (), {"name": "DummyAgent"})
                    self.starting_agent = DummyAgent
                    return {"DummyAgent": DummyAgent}
            blueprint_instance = DummyBlueprint(config=config)
        else:
            return Response({"error": f"Model '{model}' not found."}, status=404)
    else:
        blueprint_class = blueprint_meta.get("blueprint_class")
        if not blueprint_class:
            return Response({"error": f"Blueprint class for model '{model}' is not defined."}, status=500)
        try:
            blueprint_instance = blueprint_class(config=config)
            active_agent = context_variables.get("active_agent_name", "Assistant")
            if active_agent not in blueprint_instance.swarm.agents:
                logger.debug(f"No active agent parsed from context_variables")
            else:
                logger.debug(f"Using active agent: {active_agent}")
                blueprint_instance.set_active_agent(active_agent)
        except Exception as e:
            logger.error(f"Error initializing blueprint: {e}", exc_info=True)
            return Response({"error": f"Error initializing blueprint: {str(e)}"}, status=500)
    
    try:
        redis_client = None
        if conversation_id:
            try:
                import redis
                redis_client = redis.Redis()
                history_raw = redis_client.get(conversation_id)
                if history_raw and isinstance(history_raw, (str, bytes, bytearray)):
                    past_messages = json.loads(history_raw)
                else:
                    past_messages = []
            except Exception as e:
                logger.error(f"Error retrieving conversation history: {e}", exc_info=True)
                past_messages = []
            messages = past_messages + messages
    
        result = blueprint_instance.run_with_context(messages, context_variables)
        response_obj = result["response"]
        updated_context = result["context_variables"]
    
        if hasattr(response_obj, "model_dump"):
            response_obj = response_obj.model_dump()
        serialized = serialize_swarm_response(response_obj, model, updated_context)
        if conversation_id:
            serialized["conversation_id"] = conversation_id
            try:
                full_history = messages + [response_obj]
                if redis_client:
                    redis_client.set(conversation_id, json.dumps(full_history))
            except Exception as e:
                logger.error(f"Error storing conversation history: {e}", exc_info=True)
        return Response(serialized, status=200)
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        return Response({"error": f"Error during execution: {str(e)}"}, status=500)

@csrf_exempt
def list_models(request):
    """
    Lists discovered blueprint folders as models.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed. Use GET."}, status=405)

    try:
        data = [
            {
                "id": key,
                "object": "model",
                "title": meta.get("title", "No title"),
                "description": meta.get("description", "No description"),
            }
            for key, meta in blueprints_metadata.items()
        ]
        return JsonResponse({"object": "list", "data": data}, status=200)
    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        return JsonResponse({"error": "Internal Server Error"}, status=500)


    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['conversations'] = ChatConversation.objects.filter(
            user=self.request.user
        ).exclude(conversation=[])  # Excluding empty conversations
        return context


    def post(self, request, *args, **kwargs):
        conversation = ChatConversation.objects.create(user=request.user)
        return redirect(reverse('chat_page', args=[conversation.pk]))


    template_name = 'chat.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation_id = self.kwargs.get('conversation_id')
        if conversation_id:
            conversation = get_object_or_404(ChatConversation, id=conversation_id, user=self.request.user)
            context['conversation'] = conversation
        else:
            context['conversation'] = None
        return context


@csrf_exempt
def django_chat_webpage(request, blueprint_name):
    return render(request, 'django_chat_webpage.html', {'conversation_id': conversation_id, 'blueprint_name': blueprint_name})


@csrf_exempt
def blueprint_webpage(request, blueprint_name):
    """
    Serves a webpage for a specific blueprint.

    Args:
        request: The HTTP request object.
        blueprint_name (str): The name of the blueprint.

    Returns:
        HttpResponse: The rendered blueprint webpage or a 404 error.
    """
    logger.debug(f"Received request for blueprint webpage: '{blueprint_name}'")
    if blueprint_name not in blueprints_metadata:
        logger.warning(f"Blueprint '{blueprint_name}' not found.")
        available_blueprints = "".join(f"<li>{bp}</li>" for bp in blueprints_metadata)
        return HttpResponse(
            f"<h1>Blueprint '{blueprint_name}' not found.</h1><p>Available blueprints:</p><ul>{available_blueprints}</ul>",
            status=404,
        )

    logger.debug(f"Rendering blueprint webpage for: '{blueprint_name}'")
    context = {
        "blueprint_name": blueprint_name,
        "dark_mode": request.session.get('dark_mode', True)  # Default to dark mode
    }
    return render(request, "simple_blueprint_page.html", context)

@csrf_exempt
def chatbot(request):
    """
    Serves a webpage for a specific blueprint.

    Args:
        request: The HTTP request object.
        blueprint_name (str): The name of the blueprint.

    Returns:
        HttpResponse: The rendered blueprint webpage or a 404 error.
    """
    logger.debug("Rendering chatbot webui")
    context = {
        "dark_mode": request.session.get('dark_mode', True)  # Default to dark mode
    }
    return render(request, "rest_mode/chatbot.html", context)


DEFAULT_CONFIG = {
    "llm": {
            "provider": "openai",
            "model": "llama3.2:latest",
            "base_url": "http://localhost:11434/v1",
            "api_key": "",
            "temperature": 0.3
        }
    }

def serve_swarm_config(request):
    config_path = Path(settings.BASE_DIR) / "swarm_config.json"
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        return JsonResponse(config_data)
    except FileNotFoundError:
        logger.error(f"swarm_config.json not found at {config_path}")
        return JsonResponse(DEFAULT_CONFIG)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {config_path}: {e}")
        return JsonResponse({"error": "Invalid JSON format in configuration file."}, status=500)

