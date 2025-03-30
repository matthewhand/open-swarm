import logging
import json
import uuid
import time
import asyncio
from typing import Dict, Any, AsyncGenerator, List, Optional

from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse, Http404, HttpRequest, HttpResponse, HttpResponseBase
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny # Keep AllowAny import
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound, APIException, ParseError, NotAuthenticated

from asgiref.sync import sync_to_async

# Assuming serializers are in the same app
from swarm.serializers import ChatCompletionRequestSerializer
# Assuming utils are in the same app/directory level
from .utils import get_blueprint_instance, validate_model_access, get_available_blueprints
# *** REMOVE or COMMENT OUT this import if present ***
# from swarm.permissions import HasValidTokenOrSession

logger = logging.getLogger(__name__)
print_logger = logging.getLogger('print_debug')

# ==============================================================================
# API Views (DRF based)
# ==============================================================================

class HealthCheckView(APIView):
    permission_classes = [AllowAny] # Health check should always be allowed
    def get(self, request, *args, **kwargs): return Response({"status": "ok"})

class ChatCompletionsView(APIView):
    """
    Handles chat completion requests, compatible with OpenAI API.
    Permissions are now handled by DEFAULT_PERMISSION_CLASSES in settings.py.
    """
    # *** REMOVED explicit permission_classes = [HasValidTokenOrSession] ***
    serializer_class = ChatCompletionRequestSerializer # Define serializer for schema generation

    async def _handle_non_streaming(self, blueprint_instance, messages: List[Dict[str, str]], request_id: str, model_name: str) -> Response:
        logger.info(f"[ReqID: {request_id}] Processing non-streaming request for model '{model_name}'.")
        final_response_data = None; start_time = time.time()
        try:
            # Assuming blueprint_instance.run is now correctly async def
            async_generator = blueprint_instance.run(messages) # No await needed here if it returns the generator
            async for chunk in async_generator:
                if isinstance(chunk, dict) and "messages" in chunk: final_response_data = chunk["messages"]; logger.debug(f"[ReqID: {request_id}] Received final data chunk: {final_response_data}"); break
                else: logger.warning(f"[ReqID: {request_id}] Unexpected chunk format: {chunk}")

            if not final_response_data or not isinstance(final_response_data, list) or not final_response_data:
                 logger.error(f"[ReqID: {request_id}] Blueprint '{model_name}' did not return valid final data structure. Got: {final_response_data}")
                 raise APIException("Blueprint did not return valid data.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if not isinstance(final_response_data[0], dict) or 'role' not in final_response_data[0]:
                 logger.error(f"[ReqID: {request_id}] Blueprint '{model_name}' returned invalid message structure. Got: {final_response_data[0]}")
                 raise APIException("Blueprint returned invalid message structure.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            response_payload = { "id": f"chatcmpl-{request_id}", "object": "chat.completion", "created": int(time.time()), "model": model_name, "choices": [{"index": 0, "message": final_response_data[0], "logprobs": None, "finish_reason": "stop"}], "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "system_fingerprint": None }
            end_time = time.time(); logger.info(f"[ReqID: {request_id}] Non-streaming request completed in {end_time - start_time:.2f}s.")
            return Response(response_payload, status=status.HTTP_200_OK)
        except APIException: raise
        except Exception as e: logger.error(f"[ReqID: {request_id}] Unexpected error during non-streaming blueprint execution: {e}", exc_info=True); raise APIException(f"Internal server error during generation: {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e

    async def _handle_streaming(self, blueprint_instance, messages: List[Dict[str, str]], request_id: str, model_name: str) -> StreamingHttpResponse:
        logger.info(f"[ReqID: {request_id}] Processing streaming request for model '{model_name}'.")
        async def event_stream():
            start_time = time.time(); chunk_index = 0
            try:
                logger.debug(f"[ReqID: {request_id}] Getting async generator from blueprint run...");
                # Assuming blueprint_instance.run is now correctly async def
                async_generator = blueprint_instance.run(messages) # No await needed here
                logger.debug(f"[ReqID: {request_id}] Got async generator. Starting iteration...")
                async for chunk in async_generator:
                    logger.debug(f"[ReqID: {request_id}] Received stream chunk {chunk_index}: {chunk}")
                    if not isinstance(chunk, dict) or "messages" not in chunk or not isinstance(chunk["messages"], list) or not chunk["messages"] or not isinstance(chunk["messages"][0], dict):
                        logger.warning(f"[ReqID: {request_id}] Skipping invalid chunk format: {chunk}"); continue
                    delta_content = chunk["messages"][0].get("content", "");
                    delta = {"role": "assistant"}
                    if delta_content is not None: delta["content"] = delta_content

                    response_chunk = { "id": f"chatcmpl-{request_id}", "object": "chat.completion.chunk", "created": int(time.time()), "model": model_name, "choices": [{"index": 0, "delta": delta, "logprobs": None, "finish_reason": None}] }
                    logger.debug(f"[ReqID: {request_id}] Sending SSE chunk {chunk_index}"); yield f"data: {json.dumps(response_chunk)}\n\n"; chunk_index += 1; await asyncio.sleep(0.01) # Small sleep to yield control
                logger.debug(f"[ReqID: {request_id}] Finished iterating stream. Sending [DONE]."); yield "data: [DONE]\n\n"; end_time = time.time(); logger.info(f"[ReqID: {request_id}] Streaming request completed in {end_time - start_time:.2f}s.")
            except APIException as e:
                 logger.error(f"[ReqID: {request_id}] API error during streaming blueprint execution: {e}", exc_info=True); error_msg = f"API error during stream: {e.detail}"; error_chunk = {"error": {"message": error_msg, "type": "api_error", "code": e.status_code}}
                 try: yield f"data: {json.dumps(error_chunk)}\n\n"; yield "data: [DONE]\n\n"
                 except Exception as send_err: logger.error(f"[ReqID: {request_id}] Failed to send error chunk: {send_err}")
            except Exception as e:
                 logger.error(f"[ReqID: {request_id}] Unexpected error during streaming blueprint execution: {e}", exc_info=True); error_msg = f"Internal server error during stream: {str(e)}"; error_chunk = {"error": {"message": error_msg, "type": "internal_error"}}
                 try: yield f"data: {json.dumps(error_chunk)}\n\n"; yield "data: [DONE]\n\n"
                 except Exception as send_err: logger.error(f"[ReqID: {request_id}] Failed to send error chunk: {send_err}")
        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

    @method_decorator(csrf_exempt)
    async def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.args = args; self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request; self.headers = self.default_response_headers
        try:
            print_logger.debug(f"User before initial(): {getattr(request, 'user', 'N/A')}, Auth before initial(): {getattr(request, 'auth', 'N/A')}")
            # DRF's initial performs auth and permission checks synchronously
            await sync_to_async(self.initial)(request, *args, **kwargs)
            print_logger.debug(f"User after initial(): {getattr(request, 'user', 'N/A')}, Auth after initial(): {getattr(request, 'auth', 'N/A')}")

            if request.method.lower() in self.http_method_names: handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
            else: handler = self.http_method_not_allowed

            # Check if handler is async (which post should be)
            if asyncio.iscoroutinefunction(handler):
                response = await handler(request, *args, **kwargs)
            else:
                 response = await sync_to_async(handler)(request, *args, **kwargs) # Wrap sync handlers if any
        except Exception as exc: response = self.handle_exception(exc)
        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    async def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        request_id = str(uuid.uuid4()); logger.info(f"[ReqID: {request_id}] Received chat completion request.")
        print_logger.debug(f"[ReqID: {request_id}] User at start of post: {getattr(request, 'user', 'N/A')}, Auth: {getattr(request, 'auth', 'N/A')}")
        try:
            request_data = request.data
        except ParseError as e: logger.error(f"[ReqID: {request_id}] Invalid JSON body: {e.detail}"); raise e
        except json.JSONDecodeError as e: logger.error(f"[ReqID: {request_id}] JSON Decode Error: {e}"); raise ParseError(f"Invalid JSON body: {e}")

        serializer = self.serializer_class(data=request_data) # Use self.serializer_class
        try:
            print_logger.debug(f"[ReqID: {request_id}] Attempting serializer.is_valid(). Data: {request_data}")
            serializer.is_valid(raise_exception=True)
            print_logger.debug(f"[ReqID: {request_id}] Serializer is_valid() PASSED.")
        except ValidationError as e: print_logger.error(f"[ReqID: {request_id}] Serializer validation FAILED: {e.detail}"); raise e
        except Exception as e: print_logger.error(f"[ReqID: {request_id}] UNEXPECTED error during serializer validation: {e}", exc_info=True); raise APIException(f"Internal error during request validation: {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e

        validated_data = serializer.validated_data
        model_name = validated_data['model']
        messages = validated_data['messages']
        stream = validated_data.get('stream', False)
        blueprint_params = validated_data.get('params', None)

        print_logger.debug(f"[ReqID: {request_id}] Validation passed. Checking model access for user {request.user} and model {model_name}")
        # Wrap sync validate_model_access
        access_granted = await sync_to_async(validate_model_access)(request.user, model_name)
        if not access_granted:
             logger.warning(f"[ReqID: {request_id}] User {request.user} denied access to model '{model_name}'.")
             raise PermissionDenied(f"You do not have permission to access the model '{model_name}'.")

        print_logger.debug(f"[ReqID: {request_id}] Access granted. Getting blueprint instance for {model_name}")
        # get_blueprint_instance is async
        blueprint_instance = await get_blueprint_instance(model_name, params=blueprint_params)

        if blueprint_instance is None:
            logger.error(f"[ReqID: {request_id}] Blueprint '{model_name}' not found or failed to initialize after access checks.")
            raise NotFound(f"The requested model (blueprint) '{model_name}' was not found or could not be initialized.")

        if stream: return await self._handle_streaming(blueprint_instance, messages, request_id, model_name)
        else: return await self._handle_non_streaming(blueprint_instance, messages, request_id, model_name)

# ==============================================================================
# Web UI Views (Django standard views) - Keep commented if not used
# ==============================================================================
# @login_required
# def index(request):
#     # Assuming get_available_blueprints is sync or wrapped appropriately elsewhere
#     available_bps = get_available_blueprints() # Needs to be sync or wrapped
#     context = { 'user': request.user, 'available_blueprints': list(available_bps.keys()), }
#     return render(request, 'swarm/index.html', context)
