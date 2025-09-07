
# --- Content for src/swarm/views/chat_views.py ---
import asyncio
import json
import logging
import sys
import time
import uuid
from typing import Any

# Utility to wrap sync functions for async execution
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpRequest,
    HttpResponseBase,
    StreamingHttpResponse,
)
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    ParseError,
    PermissionDenied,
    ValidationError,
)
from rest_framework.permissions import AllowAny
from rest_framework.request import Request  # Import DRF Request
from rest_framework.response import Response
from rest_framework.views import APIView

# Import custom permission
# Assuming serializers are in the same app
from swarm.serializers import ChatCompletionRequestSerializer

# Assuming utils are in the same app/directory level
# Make sure these utils are async-safe or wrapped if they perform sync I/O
from .utils import (
    get_available_blueprints,
    get_blueprint_instance,
    validate_model_access,
)

logger = logging.getLogger(__name__)
# Specific logger for debug prints, potentially configured differently
print_logger = logging.getLogger('print_debug')

# Bridge module aliasing between 'swarm' and 'src.swarm' so test patches hit the correct module
try:
    if __name__ == 'swarm.views.chat_views':
        sys.modules.setdefault('src.swarm.views.chat_views', sys.modules[__name__])
    elif __name__ == 'src.swarm.views.chat_views':
        sys.modules.setdefault('swarm.views.chat_views', sys.modules[__name__])
except Exception:
    pass

# ==============================================================================
# API Views (DRF based)
# ==============================================================================

class HealthCheckView(APIView):
    """ Simple health check endpoint. """
    permission_classes = [AllowAny]
    def get(self, request, *args, **kwargs):
        """ Returns simple 'ok' status. """
        return Response({"status": "ok"})

class ChatCompletionsView(APIView):
    """
    Handles chat completion requests (/v1/chat/completions), compatible with OpenAI API spec.
    Supports both streaming and non-streaming responses.
    Uses asynchronous handling for potentially long-running blueprint operations.
    """
    # Default serializer class for request validation.
    serializer_class = ChatCompletionRequestSerializer
    # Default permission classes are likely set in settings.py
    # permission_classes = [IsAuthenticated] # Example default

    # --- Internal Helper Methods (Unchanged) ---

    async def _handle_non_streaming(self, blueprint_instance, messages: list[dict[str, str]], request_id: str, model_name: str) -> Response:
        """ Handles non-streaming requests. """
        logger.info(f"[ReqID: {request_id}] Processing non-streaming request for model '{model_name}'.")
        final_response_data = None; start_time = time.time()
        try:
            # The blueprint's run method should be an async generator.
            async_generator = blueprint_instance.run(messages, stream=False)
            async for chunk in async_generator:
                # Accept either internal {messages:[{role,content}]} or OpenAI-like completion objects
                if isinstance(chunk, dict):
                    if "messages" in chunk and isinstance(chunk["messages"], list):
                        final_response_data = chunk["messages"]
                        logger.debug(f"[ReqID: {request_id}] Received final data chunk (messages list).")
                        break
                    if "choices" in chunk and isinstance(chunk.get("choices"), list) and chunk["choices"]:
                        choice0 = chunk["choices"][0]
                        message = choice0.get("message") or {}
                        if isinstance(message, dict) and message.get("role") and (message.get("content") is not None):
                            final_response_data = [message]
                            logger.debug(f"[ReqID: {request_id}] Received final data chunk (OpenAI object).")
                            break
                logger.warning(f"[ReqID: {request_id}] Unexpected chunk format during non-streaming run: {chunk}")

            if not final_response_data or not isinstance(final_response_data, list) or not final_response_data:
                 logger.error(f"[ReqID: {request_id}] Blueprint '{model_name}' did not return a valid final message list. Got: {final_response_data}")
                 raise APIException("Blueprint did not return valid data.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if not isinstance(final_response_data[0], dict) or 'role' not in final_response_data[0]:
                 logger.error(f"[ReqID: {request_id}] Blueprint '{model_name}' returned invalid message structure. Got: {final_response_data[0]}")
                 raise APIException("Blueprint returned invalid message structure.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            response_payload = { "id": f"chatcmpl-{request_id}", "object": "chat.completion", "created": int(time.time()), "model": model_name, "choices": [{"index": 0, "message": final_response_data[0], "logprobs": None, "finish_reason": "stop"}], "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "system_fingerprint": None }
            end_time = time.time(); logger.info(f"[ReqID: {request_id}] Non-streaming request completed in {end_time - start_time:.2f}s.")
            return Response(response_payload, status=status.HTTP_200_OK)
        except APIException: raise
        except Exception as e: logger.error(f"[ReqID: {request_id}] Unexpected error during non-streaming blueprint execution: {e}", exc_info=True); raise APIException(f"Internal server error during generation: {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e

    async def _handle_streaming(self, blueprint_instance, messages: list[dict[str, str]], request_id: str, model_name: str) -> StreamingHttpResponse:
        """ Handles streaming requests using SSE. """
        logger.info(f"[ReqID: {request_id}] Processing streaming request for model '{model_name}'.")
        async def event_stream():
            start_time = time.time(); chunk_index = 0
            try:
                logger.debug(f"[ReqID: {request_id}] Getting async generator from blueprint.run()..."); async_generator = blueprint_instance.run(messages, stream=True); logger.debug(f"[ReqID: {request_id}] Got async generator. Starting iteration...")
                async for chunk in async_generator:
                    logger.debug(f"[ReqID: {request_id}] Received stream chunk {chunk_index}: {chunk}")
                    delta = {"role": "assistant"}
                    if isinstance(chunk, dict):
                        if "messages" in chunk and isinstance(chunk["messages"], list) and chunk["messages"] and isinstance(chunk["messages"][0], dict):
                            delta_content = chunk["messages"][0].get("content")
                            if delta_content is not None:
                                delta["content"] = delta_content
                        elif "choices" in chunk and isinstance(chunk.get("choices"), list) and chunk["choices"]:
                            # Handle OpenAI-like streaming or completion chunk shapes
                            choice0 = chunk["choices"][0]
                            if isinstance(choice0, dict):
                                # delta content (streaming) or message content (completion)
                                message = choice0.get("delta") or choice0.get("message") or {}
                                if isinstance(message, dict) and (message.get("content") is not None):
                                    delta["content"] = message.get("content")
                    if "content" not in delta:
                        logger.warning(f"[ReqID: {request_id}] Skipping invalid chunk format: {chunk}")
                        continue
                    response_chunk = { "id": f"chatcmpl-{request_id}", "object": "chat.completion.chunk", "created": int(time.time()), "model": model_name, "choices": [{"index": 0, "delta": delta, "logprobs": None, "finish_reason": None}] }
                    logger.debug(f"[ReqID: {request_id}] Sending SSE chunk {chunk_index}"); yield f"data: {json.dumps(response_chunk)}\n\n"; chunk_index += 1; await asyncio.sleep(0.01)
                logger.debug(f"[ReqID: {request_id}] Finished iterating stream. Sending [DONE]."); yield "data: [DONE]\n\n"; end_time = time.time(); logger.info(f"[ReqID: {request_id}] Streaming request completed in {end_time - start_time:.2f}s.")
            except APIException as e: logger.error(f"[ReqID: {request_id}] API error during streaming: {e}", exc_info=True); error_msg = f"API error: {e.detail}"; error_chunk = {"error": {"message": error_msg, "type": "api_error", "code": e.status_code}}; yield f"data: {json.dumps(error_chunk)}\n\n"; yield "data: [DONE]\n\n"
            except Exception as e: logger.error(f"[ReqID: {request_id}] Unexpected error during streaming: {e}", exc_info=True); error_msg = f"Internal server error: {str(e)}"; error_chunk = {"error": {"message": error_msg, "type": "internal_error"}}; yield f"data: {json.dumps(error_chunk)}\n\n"; yield "data: [DONE]\n\n"
        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

    # --- Restore Custom dispatch method (wrapping perform_authentication) ---
    @method_decorator(csrf_exempt)
    async def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """
        Override DRF's dispatch method to specifically wrap the authentication step.
        """
        self.args = args
        self.kwargs = kwargs
        drf_request: Request = self.initialize_request(request, *args, **kwargs)
        self.request = drf_request
        self.headers = self.default_response_headers

        response = None
        try:
            # --- Wrap ONLY perform_authentication ---
            print_logger.debug(f"User before perform_authentication: {getattr(drf_request, 'user', 'N/A')}, Auth: {getattr(drf_request, 'auth', 'N/A')}")
            # This forces the synchronous DB access within perform_authentication into a thread
            await sync_to_async(self.perform_authentication)(drf_request)
            print_logger.debug(f"User after perform_authentication: {getattr(drf_request, 'user', 'N/A')}, Auth: {getattr(drf_request, 'auth', 'N/A')}")
            # --- End wrapping ---

            # Enforce auth: if ENABLE_API_AUTH is True, require valid token or authenticated session
            if bool(getattr(settings, 'ENABLE_API_AUTH', False)):
                has_token = getattr(drf_request, 'auth', None) is not None
                user_obj = getattr(drf_request, 'user', None)
                is_authenticated = bool(user_obj and getattr(user_obj, 'is_authenticated', False))
                if not (has_token or is_authenticated):
                    raise PermissionDenied('Authentication credentials were not provided')

            # Run permission and throttle checks synchronously after auth.
            # These checks operate on the now-populated request.user/auth attributes.
            self.check_permissions(drf_request)
            print_logger.debug("Permissions check passed.")
            self.check_throttles(drf_request)
            print_logger.debug("Throttles check passed.")

            # Find and execute the handler (e.g., post).
            if drf_request.method.lower() in self.http_method_names:
                handler = getattr(self, drf_request.method.lower(), self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            # IMPORTANT: Await the handler if it's async (like self.post)
            if asyncio.iscoroutinefunction(handler):
                response = await handler(drf_request, *args, **kwargs)
            else:
                # Wrap sync handlers if any exist (like GET, OPTIONS).
                response = await sync_to_async(handler)(drf_request, *args, **kwargs)

        except Exception as exc:
            # Let DRF handle exceptions to generate appropriate responses
            response = self.handle_exception(exc)

        # Finalize response should now receive a valid Response/StreamingHttpResponse
        self.response = self.finalize_response(drf_request, response, *args, **kwargs)
        return self.response

    # --- POST Handler (Keep sync_to_async wrappers here too) ---
    async def post(self, request: Request, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """
        Handles POST requests for chat completions. Assumes dispatch has handled auth/perms.
        """
        request_id = str(uuid.uuid4())
        logger.info(f"[ReqID: {request_id}] Processing POST request.")
        print_logger.debug(f"[ReqID: {request_id}] User in post: {getattr(request, 'user', 'N/A')}, Auth: {getattr(request, 'auth', 'N/A')}")

        # --- Request Body Parsing & Validation ---
        try: request_data = request.data
        except ParseError as e: logger.error(f"[ReqID: {request_id}] Invalid request body format: {e.detail}"); raise e
        except json.JSONDecodeError as e: logger.error(f"[ReqID: {request_id}] JSON Decode Error: {e}"); raise ParseError(f"Invalid JSON body: {e}")

        # --- Serialization and Validation ---
        serializer = self.serializer_class(data=request_data)
        try:
            print_logger.debug(f"[ReqID: {request_id}] Validating request data: {request_data}")
            # Wrap sync is_valid call as it *might* do DB lookups
            await sync_to_async(serializer.is_valid)(raise_exception=True)
            print_logger.debug(f"[ReqID: {request_id}] Request data validation successful.")
        except ValidationError as e: print_logger.error(f"[ReqID: {request_id}] Request data validation FAILED: {e.detail}"); raise e
        except Exception as e: print_logger.error(f"[ReqID: {request_id}] Unexpected error during serializer validation: {e}", exc_info=True); raise APIException(f"Internal error during request validation: {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e

        validated_data = serializer.validated_data
        model_name = validated_data['model']
        messages = validated_data['messages']
        stream = validated_data.get('stream', False)
        blueprint_params = validated_data.get('params', None)

        # --- Model Access Validation ---
        # This function likely performs sync DB lookups, so wrap it.
        print_logger.debug(f"[ReqID: {request_id}] Checking model access for user '{request.user}' and model '{model_name}'")
        try:
            access_granted = await sync_to_async(validate_model_access)(request.user, model_name)
        except Exception as e:
            logger.error(f"[ReqID: {request_id}] Error during model access validation for model '{model_name}': {e}", exc_info=True)
            raise APIException("Error checking model permissions.", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e

        # --- Get Blueprint Instance (existence determines 404) ---
        # This function should ideally be async or sync-safe.
        print_logger.debug(f"[ReqID: {request_id}] Getting blueprint instance for '{model_name}' with params: {blueprint_params}")
        try:
            blueprint_instance = await get_blueprint_instance(model_name, params=blueprint_params)
        except Exception as e:
             logger.error(f"[ReqID: {request_id}] Error getting blueprint instance for '{model_name}': {e}", exc_info=True)
             raise APIException(f"Failed to load model '{model_name}': {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e

        if blueprint_instance is None:
            logger.error(f"[ReqID: {request_id}] Blueprint '{model_name}' not found or failed to initialize (get_blueprint_instance returned None).")
            raise NotFound(f"The requested model (blueprint) '{model_name}' was not found or could not be initialized.")

        # Only after confirming existence, enforce permission check result
        if not access_granted:
            logger.warning(f"[ReqID: {request_id}] User '{request.user}' denied access to model '{model_name}'.")
            raise PermissionDenied(f"You do not have permission to access the model '{model_name}'.")

        # --- Handle Streaming or Non-Streaming Response ---
        if stream:
            return await self._handle_streaming(blueprint_instance, messages, request_id, model_name)
        else:
            return await self._handle_non_streaming(blueprint_instance, messages, request_id, model_name)


# ==============================================================================
# Simple Django Views (Example for Web UI - if ENABLE_WEBUI=True)
# ==============================================================================

@method_decorator(csrf_exempt, name='dispatch') # Apply csrf_exempt if needed
@method_decorator(login_required, name='dispatch') # Require login
class IndexView(View):
    """ Renders the main chat interface page. """
    def get(self, request):
        """ Handles GET requests to render the index page. """
        # Assuming get_available_blueprints is sync safe
        available_blueprints = get_available_blueprints()
        context = {
            'available_blueprints': available_blueprints,
            'user': request.user, # User should be available here
        }
        return render(request, 'index.html', context)
