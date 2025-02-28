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
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# Django & DRF imports
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView as BaseSpectacularAPIView

class HiddenSpectacularAPIView(BaseSpectacularAPIView):
    exclude_from_schema = True

SpectacularAPIView = HiddenSpectacularAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication
from rest_framework.viewsets import ModelViewSet

# Project-specific imports
from swarm.auth import EnvOrTokenAuthentication
from swarm.models import ChatConversation, ChatMessage
from swarm.extensions.blueprint import discover_blueprints
from swarm.extensions.blueprint.blueprint_base import BlueprintBase
from swarm.extensions.config.config_loader import load_server_config, load_llm_config
from swarm.utils.logger_setup import setup_logger
from swarm.utils.redact import redact_sensitive_data
from swarm.utils.general_utils import extract_chat_id
from swarm.extensions.blueprint.blueprint_utils import filter_blueprints

from .settings import DJANGO_DATABASE
from .models import ChatMessage
from .serializers import ChatMessageSerializer

# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------

logger = setup_logger(__name__)

REDIS_AVAILABLE = bool(os.getenv("STATEFUL_CHAT_ID_PATH"))
redis_client = None
if REDIS_AVAILABLE:
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
        redis_client.ping()
        logger.info("✅ Redis connection successful.")
    except Exception as e:
        logger.warning(f"⚠️ Redis unavailable, falling back to PostgreSQL: {e}")
        REDIS_AVAILABLE = False

CONFIG_PATH = Path('/app/swarm_config.json')
try:
    config = load_server_config(str(CONFIG_PATH))
except Exception as e:
    logger.critical(f"Failed to load configuration from {CONFIG_PATH}: {e}")
    raise e

BLUEPRINTS_DIR = Path('/app/blueprints')
try:
    all_blueprints = discover_blueprints([str(BLUEPRINTS_DIR)])
    if allowed_blueprints := os.getenv("SWARM_BLUEPRINTS"):
        blueprints_metadata = filter_blueprints(all_blueprints, allowed_blueprints)
        logger.info(f"Filtered blueprints using SWARM_BLUEPRINTS: {allowed_blueprints.split(',')}")
    else:
        blueprints_metadata = all_blueprints
    redacted_blueprints_metadata = redact_sensitive_data(blueprints_metadata)
    logger.debug(f"Discovered blueprints metadata: {redacted_blueprints_metadata}")
except Exception as e:
    logger.error(f"Error discovering blueprints: {e}", exc_info=True)
    raise e

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

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def serialize_swarm_response(response: Any, model_name: str, context_variables: Dict[str, Any]) -> Dict[str, Any]:
    logger.debug(f"Serializing Swarm response, type: {type(response)}, model: {model_name}")
    if hasattr(response, 'messages'):
        messages = response.messages
        logger.debug(f"Extracted messages from Response object: {json.dumps(messages, indent=2)}")
    elif isinstance(response, dict):
        messages = response.get("messages", [])
        logger.debug(f"Extracted messages from dict: {json.dumps(messages, indent=2)}")
    elif isinstance(response, str):
        logger.warning(f"Received string response instead of dictionary: {response[:100]}{'...' if len(response) > 100 else ''}, treating as message content")
        messages = [{"role": "assistant", "content": response}]
    else:
        logger.error(f"Unexpected response type: {type(response)}, defaulting to empty response")
        messages = []

    def remove_functions(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: remove_functions(v) for k, v in obj.items() if k != "functions" and not callable(v)}
        elif hasattr(obj, "__dict__"):
            obj_dict = {k: v for k, v in obj.__dict__.items() if k != "functions" and not callable(v)}
            return {k: remove_functions(v) for k, v in obj_dict.items()}
        elif isinstance(obj, list):
            return [remove_functions(item) for item in obj if not callable(item)]
        elif isinstance(obj, tuple):
            return tuple(remove_functions(item) for item in obj if not callable(item))
        return obj

    response_dict = response.__dict__ if hasattr(response, '__dict__') else response
    try:
        safe_response = remove_functions(response_dict)
        safe_context = remove_functions(context_variables)
        logger.debug(f"Cleaned response: {json.dumps(safe_response, indent=2) if isinstance(safe_response, dict) else str(safe_response)[:500]}")
        logger.debug(f"Cleaned context variables: {json.dumps(safe_context, indent=2)[:1000]}")
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to log response or context due to serialization error: {str(e)}")
        logger.debug(f"Response type: {type(response)}, Context type: {type(context_variables)}")

    if hasattr(response, 'agent'):
        response_dict['agent'] = remove_functions(response.agent)
    elif isinstance(response_dict, dict) and "agent" in response_dict:
        response_dict["agent"] = remove_functions(response_dict["agent"])

    clean_context = remove_functions(context_variables)
    clean_response = remove_functions(response_dict)

    formatted_messages = []
    for i, msg in enumerate(messages):
        logger.debug(f"Processing message {i}: {json.dumps(msg, indent=2)}")
        if msg.get("role") == "assistant" and msg.get("content"):
            formatted_msg = {
                "index": len(formatted_messages),
                "message": {
                    "role": "assistant",
                    "content": msg["content"]
                },
                "finish_reason": "stop"
            }
            formatted_messages.append(formatted_msg)
            logger.debug(f"Added to choices from loop: {json.dumps(formatted_msg, indent=2)}")

    if messages and messages[-1].get("role") == "assistant" and messages[-1].get("content"):
        last_content = messages[-1]["content"]
        if not any(m["message"]["content"] == last_content for m in formatted_messages):
            formatted_msg = {
                "index": len(formatted_messages),
                "message": {
                    "role": "assistant",
                    "content": last_content
                },
                "finish_reason": "stop"
            }
            formatted_messages.append(formatted_msg)
            logger.debug(f"Added last message via failsafe: {json.dumps(formatted_msg, indent=2)}")

    if not formatted_messages:
        logger.warning("No assistant messages with content found for 'choices' after all checks")

    logger.debug(f"Final formatted_messages: {json.dumps(formatted_messages, indent=2)}")

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    for msg in messages:
        if msg.get("content"):
            token_count = len(msg["content"].split())
            if msg.get("role") == "user":
                prompt_tokens += token_count
            elif msg.get("role") == "assistant":
                completion_tokens += token_count
            total_tokens += token_count
        if msg.get("tool_calls"):
            total_tokens += 1  # Rough estimate for tool call presence

    return {
        "id": f"swarm-chat-completion-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": formatted_messages,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        },
        "context_variables": clean_context,
        "full_response": clean_response
    }

def parse_chat_request(request: Any) -> Any:
    try:
        body = json.loads(request.body)
        model = body.get("model", "default")
        messages = body.get("messages", [])
        if not messages and "message" in body:
            messages = [body["message"]]
        messages = [msg if isinstance(msg, dict) else {"content": msg} for msg in messages]
        context_variables = body.get("context_variables", {})

        conversation_id = extract_chat_id(body)
        tool_call_id = None
        if messages:
            last_message = messages[-1]
            tool_calls = last_message.get("tool_calls", [])
            if tool_calls:
                tool_call_id = tool_calls[-1].get("id")

        if not conversation_id and 'STATEFUL_CHAT_ID_PATH' in os.environ:
            conversation_id = str(uuid.uuid4())
            logger.warning(f"⚠️ No conversation_id detected, generating new ID: {conversation_id}")

        for idx, msg in enumerate(messages):
            if "role" not in msg:
                messages[idx]["role"] = "user"

        if not messages:
            return Response({"error": "Messages are required."}, status=400)

        return (body, model, messages, context_variables, conversation_id, tool_call_id)
    except json.JSONDecodeError:
        return Response({"error": "Invalid JSON payload."}, status=400)

def get_blueprint_instance(model: str, context_vars: dict) -> Any:
    blueprint_meta = blueprints_metadata.get(model)
    if not blueprint_meta:
        if model == "default":
            class DummyBlueprint(BlueprintBase):
                metadata = {"title": "Dummy Blueprint", "env_vars": []}
                def create_agents(self) -> dict:
                    DummyAgent = type("DummyAgent", (), {"name": "DummyAgent", "mcp_servers": {}, "functions": [], "nemo_guardrails_config": ""})
                    self.starting_agent = DummyAgent
                    return {"DummyAgent": DummyAgent}
                def run_with_context(self, messages, context_variables) -> dict:
                    return {
                        "response": {"message": "Dummy response"},
                        "context_variables": context_variables
                    }
            return DummyBlueprint(config=config)
        else:
            return Response({"error": f"Model '{model}' not found."}, status=404)

    blueprint_class = blueprint_meta.get("blueprint_class")
    if not blueprint_class:
        return Response({"error": f"Blueprint class for model '{model}' is not defined."}, status=500)

    try:
        blueprint_instance = blueprint_class(config=config)
        active_agent = context_vars.get("active_agent_name", "Assistant")
        if active_agent not in blueprint_instance.swarm.agents:
            logger.debug("No active agent parsed from context_variables")
        else:
            logger.debug(f"Using active agent: {active_agent}")
            blueprint_instance.set_active_agent(active_agent)
        return blueprint_instance
    except Exception as e:
        logger.error(f"Error initializing blueprint: {e}", exc_info=True)
        return Response({"error": f"Error initializing blueprint: {str(e)}"}, status=500)

def load_conversation_history(conversation_id: Optional[str], messages: List[dict], tool_call_id: Optional[str] = None) -> List[dict]:
    if not conversation_id:
        logger.warning("⚠️ No conversation_id provided, returning only new messages.")
        return messages

    past_messages = []
    if REDIS_AVAILABLE and redis_client:
        try:
            history_raw = redis_client.get(conversation_id)
            if history_raw:
                data_str = history_raw.decode("utf-8") if isinstance(history_raw, bytes) else str(history_raw)
                past_messages = json.loads(data_str)
                logger.debug(f"✅ Retrieved {len(past_messages)} messages from Redis for conversation: {conversation_id}")
        except Exception as e:
            logger.error(f"⚠️ Error retrieving conversation history from Redis: {e}", exc_info=True)

    if not past_messages:
        try:
            conversation = ChatConversation.objects.get(conversation_id=conversation_id)
            query = conversation.messages.all()
            if tool_call_id:
                query = query.filter(tool_call_id=tool_call_id)
            past_messages = list(query.order_by("timestamp").values("sender", "content", "timestamp", "tool_call_id"))
            logger.debug(f"✅ Retrieved {len(past_messages)} messages from DB for conversation: {conversation_id}, tool_call_id: {tool_call_id}")
        except ChatConversation.DoesNotExist:
            logger.warning(f"⚠️ No existing conversation found in DB for ID: {conversation_id}")
            past_messages = []

    formatted_past_messages = [
        {
            "role": msg["sender"],
            "content": msg["content"],
            "timestamp": msg["timestamp"],
            "tool_call_id": msg.get("tool_call_id")
        }
        for msg in past_messages
    ]

    return formatted_past_messages + messages

def store_conversation_history(conversation_id, full_history, response_obj=None):
    try:
        chat, created = ChatConversation.objects.get_or_create(conversation_id=conversation_id)
        if created:
            logger.debug(f"🆕 Created new ChatConversation: {conversation_id}")
        else:
            logger.debug(f"🔄 Updating existing ChatConversation: {conversation_id}")

        stored_messages = set(chat.messages.values_list("content", flat=True))
        new_messages = []
        for msg in full_history:
            if not msg.get("content") and not msg.get("tool_calls"):
                logger.warning(f"⚠️ Skipping empty message in conversation {conversation_id}")
                continue
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            serialized_content = content if content.strip() else json.dumps(msg.get("tool_calls", {}))
            if serialized_content not in stored_messages:
                new_messages.append(ChatMessage(
                    conversation=chat,
                    sender=role,
                    content=serialized_content,
                    tool_call_id=msg.get("tool_call_id")
                ))
                stored_messages.add(serialized_content)

        if new_messages:
            ChatMessage.objects.bulk_create(new_messages)
            logger.debug(f"✅ Stored {len(new_messages)} new messages for conversation {conversation_id}")
        else:
            logger.warning(f"⚠️ No new messages to store for conversation {conversation_id}")

        if REDIS_AVAILABLE and redis_client:
            try:
                redis_client.set(conversation_id, json.dumps(full_history))
            except Exception as e:
                logger.error(f"Error updating Redis: {e}", exc_info=True)

        return True
    except Exception as e:
        logger.error(f"⚠️ Error storing conversation history: {e}", exc_info=True)
        return False

def run_conversation(blueprint_instance: Any, messages_extended: List[dict], context_vars: dict) -> Tuple[Any, dict]:
    result = blueprint_instance.run_with_context(messages_extended, context_vars)
    response_obj = result["response"]
    updated_context = result["context_variables"]
    return response_obj, updated_context

# -----------------------------------------------------------------------------
# Views
# -----------------------------------------------------------------------------

@api_view(['POST'])
@csrf_exempt
@authentication_classes([EnvOrTokenAuthentication])
@permission_classes([IsAuthenticated])
def chat_completions(request):
    if request.method != "POST":
        return Response({"error": "Method not allowed. Use POST."}, status=405)
    logger.info(f"Authenticated User: {request.user}")
    parse_result = parse_chat_request(request)
    if isinstance(parse_result, Response):
        return parse_result
    body, model, messages, context_vars, conversation_id, tool_call_id = parse_result
    llm_cfg = config.get("llm", {})
    if model in llm_cfg and llm_cfg[model].get("passthrough"):
        model_type = "llm"
    else:
        model_type = "blueprint"
    logger.info(f"Identified model type: {model_type} for model: {model}")
    blueprint_instance_response = get_blueprint_instance(model, context_vars)
    if isinstance(blueprint_instance_response, Response):
        return blueprint_instance_response
    blueprint_instance = blueprint_instance_response
    messages_extended = load_conversation_history(conversation_id, messages, tool_call_id)
    try:
        response_obj, updated_context = run_conversation(blueprint_instance, messages_extended, context_vars)
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        return Response({"error": f"Error during execution: {str(e)}"}, status=500)
    serialized = serialize_swarm_response(response_obj, model, updated_context)
    if conversation_id:
        serialized["conversation_id"] = conversation_id
        store_conversation_history(conversation_id, messages_extended, response_obj)
    return Response(serialized, status=200)

@extend_schema(
    responses={
        200: {
            "type": "object",
            "properties": {
                "object": {"type": "string"},
                "data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "object": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    }
                }
            }
        }
    },
    summary="Lists discovered blueprint folders as models."
)
@csrf_exempt
@api_view(["GET"])
@permission_classes([AllowAny])
@authentication_classes([])
def list_models(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed. Use GET."}, status=405)
    try:
        global blueprints_metadata, config
        allowed = os.getenv("SWARM_BLUEPRINTS")
        if allowed and allowed.strip():
            blueprints_metadata_local = filter_blueprints(blueprints_metadata, allowed)
        else:
            blueprints_metadata_local = blueprints_metadata
        data = [
            {
                "id": key,
                "object": "model",
                "title": meta.get("title", "No title"),
                "description": meta.get("description", "No description"),
            }
            for key, meta in blueprints_metadata_local.items()
        ]
        llm_config = config.get("llm", {})
        llm_data = [
            {
                "id": key,
                "object": "llm",
                "title": key,
                "description": ", ".join(f"{k}: {v}" for k, v in {k: v for k, v in conf.items() if k != "api_key"}.items())
            }
            for key, conf in llm_config.items() if conf.get("passthrough")
        ]
        data.extend(llm_data)
        logger.debug(f"Returning models: {data}")
        return JsonResponse({"object": "list", "data": data}, status=200)
    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        return JsonResponse({"error": "Internal Server Error"}, status=500)

@csrf_exempt
def django_chat_webpage(request, blueprint_name):
    return render(request, 'django_chat_webpage.html', {
        'conversation_id': request.GET.get("conversation_id"),
        'blueprint_name': blueprint_name
    })

@csrf_exempt
def index(request):
    logger.debug("Rendering index page")
    context = {
        "dark_mode": request.session.get('dark_mode', True),
        "enable_admin": os.getenv("ENABLE_ADMIN", "false").lower() in ("true", "1", "t"),
        "blueprints": blueprints_metadata.keys()
    }
    return render(request, "index.html", context)

@csrf_exempt
def blueprint_webpage(request, blueprint_name):
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
        "dark_mode": request.session.get('dark_mode', True),
        "is_chatbot": False
    }
    return render(request, "simple_blueprint_page.html", context)

@csrf_exempt
def chatbot_view(request):
    logger.debug("Rendering chatbot web UI")
    context = {
        "dark_mode": request.session.get('dark_mode', True),
        "is_chatbot": True
    }
    return render(request, "rest_mode/chatbot.html", context)

@csrf_exempt
def messenger(request):
    logger.debug("Rendering messenger web UI")
    context = {
        "dark_mode": request.session.get('dark_mode', True),
        "is_chatbot": False
    }
    return render(request, "rest_mode/messenger.html", context)

DEFAULT_CONFIG = {
    "llm": {
        "default": {
            "provider": "openai",
            "model": "llama3.2:latest",
            "base_url": "http://localhost:11434/v1",
            "api_key": "",
            "temperature": 0.3
        }
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

class ChatMessageViewSet(ModelViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer

    @extend_schema(summary="List all chat messages")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Retrieve a chat message by its unique id")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary="Create a new chat message")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary="Update an existing chat message")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(summary="Partially update a chat message")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(summary="Delete a chat message by its unique id")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

__all__ = ["chat_completions", "list_models", "serve_swarm_config", "ChatMessage"]
