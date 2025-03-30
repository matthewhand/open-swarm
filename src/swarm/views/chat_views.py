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
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound, APIException, ParseError

from asgiref.sync import sync_to_async

from swarm.serializers import ChatCompletionRequestSerializer
from .utils import get_blueprint_instance, validate_model_access, get_available_blueprints
from swarm.permissions import HasValidTokenOrSession # Ensure this import is correct

logger = logging.getLogger(__name__)
# Add a print logger for easier spotting in test output
print_logger = logging.getLogger('print_debug')
print_logger.setLevel(logging.DEBUG)
print_handler = logging.StreamHandler() # Prints to stderr by default
print_handler.setFormatter(logging.Formatter('%(asctime)s - PRINT_DEBUG - %(message)s'))
if not print_logger.hasHandlers(): # Avoid adding handler multiple times on reload
      print_logger.addHandler(print_handler)


# ==============================================================================
# API Views (DRF based)
# ==============================================================================

class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, *args, **kwargs): return Response({"status": "ok"})

class ChatCompletionsView(APIView):
    permission_classes = [HasValidTokenOrSession]

    async def _handle_non_streaming(self, blueprint_instance, messages: List[Dict[str, str]], request_id: str, model_name: str) -> Response:
        logger.info(f"[ReqID: {request_id}] Processing non-streaming request for model '{model_name}'.")
        final_response_data = None; start_time = time.time()
        try:
            async_generator = await blueprint_instance.run(messages)
            async for chunk in async_generator:
                if isinstance(chunk, dict) and "messages" in chunk: final_response_data = chunk["messages"]; logger.debug(f"[ReqID: {request_id}] Received final data chunk: {final_response_data}"); break
                else: logger.warning(f"[ReqID: {request_id}] Unexpected chunk format: {chunk}")
            if not final_response_data: logger.error(f"[ReqID: {request_id}] Blueprint '{model_name}' did not return valid data."); raise APIException("Blueprint did not return valid data.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
                logger.debug(f"[ReqID: {request_id}] Awaiting blueprint run..."); async_generator = await blueprint_instance.run(messages); logger.debug(f"[ReqID: {request_id}] Got async generator. Starting iteration...")
                async for chunk in async_generator:
                    logger.debug(f"[ReqID: {request_id}] Received stream chunk {chunk_index}: {chunk}")
                    if not isinstance(chunk, dict) or "messages" not in chunk: logger.warning(f"[ReqID: {request_id}] Skipping invalid chunk format: {chunk}"); continue
                    delta_content = chunk["messages"][0].get("content", ""); response_chunk = { "id": f"chatcmpl-{request_id}", "object": "chat.completion.chunk", "created": int(time.time()), "model": model_name, "choices": [{"index": 0, "delta": {"role": "assistant", "content": delta_content}, "logprobs": None, "finish_reason": None}] }
                    logger.debug(f"[ReqID: {request_id}] Sending SSE chunk {chunk_index}"); yield f"data: {json.dumps(response_chunk)}\n\n"; chunk_index += 1; await asyncio.sleep(0.01)
                logger.debug(f"[ReqID: {request_id}] Finished iterating stream. Sending [DONE]."); yield "data: [DONE]\n\n"; end_time = time.time(); logger.info(f"[ReqID: {request_id}] Streaming request completed in {end_time - start_time:.2f}s.")
            except APIException as e:
                logger.error(f"[ReqID: {request_id}] API error during streaming blueprint execution: {e}", exc_info=True)
                error_msg = f"API error during stream: {e.detail}"
                error_chunk = {"error": {"message": error_msg, "type": "api_error", "code": e.status_code}}
                try:
                    # *** FIXED Syntax: yield must be on separate lines ***
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as send_err:
                    logger.error(f"[ReqID: {request_id}] Failed to send error chunk: {send_err}")
            except Exception as e:
                logger.error(f"[ReqID: {request_id}] Unexpected error during streaming blueprint execution: {e}", exc_info=True)
                error_msg = f"Internal server error during stream: {e}"
                error_chunk = {"error": {"message": error_msg, "type": "internal_error"}}
                try:
                    # *** FIXED Syntax: yield must be on separate lines ***
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as send_err:
                    logger.error(f"[ReqID: {request_id}] Failed to send error chunk: {send_err}")
        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

    @method_decorator(csrf_exempt)
    async def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.args = args; self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request; self.headers = self.default_response_headers
        try:
            # *** DEBUG: Check user before initial ***
            print_logger.debug(f"User before initial(): {getattr(request, 'user', 'N/A')}, Auth before initial(): {getattr(request, 'auth', 'N/A')}")
            await sync_to_async(self.initial)(request, *args, **kwargs)
             # *** DEBUG: Check user after initial ***
            print_logger.debug(f"User after initial(): {getattr(request, 'user', 'N/A')}, Auth after initial(): {getattr(request, 'auth', 'N/A')}")
            if request.method.lower() in self.http_method_names: handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
            else: handler = self.http_method_not_allowed
            response = await handler(request, *args, **kwargs)
        except Exception as exc: response = self.handle_exception(exc)
        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    async def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        request_id = str(uuid.uuid4())
        logger.info(f"[ReqID: {request_id}] Received chat completion request.")
        # *** DEBUG: Check user at start of post ***
        print_logger.debug(f"[ReqID: {request_id}] User at start of post: {getattr(request, 'user', 'N/A')}, Auth: {getattr(request, 'auth', 'N/A')}")
        try: request_data = json.loads(request.body)
        except json.JSONDecodeError as e: raise ParseError(f"Invalid JSON body: {e}")

        serializer = ChatCompletionRequestSerializer(data=request_data)
        try:
            print_logger.debug(f"[ReqID: {request_id}] Attempting serializer.is_valid(). Data: {request_data}") # DEBUG
            is_valid = await sync_to_async(serializer.is_valid)(raise_exception=True) # Ensure async call if needed, though is_valid is typically sync
            print_logger.debug(f"[ReqID: {request_id}] Serializer is_valid() PASSED. Result: {is_valid}") # DEBUG
        except ValidationError as e:
            print_logger.error(f"[ReqID: {request_id}] Serializer validation FAILED: {e.detail}") # DEBUG
            # Let DRF's exception handler catch this by re-raising or just letting it propagate
            raise e
        except Exception as e:
             print_logger.error(f"[ReqID: {request_id}] UNEXPECTED error during serializer validation: {e}", exc_info=True) # DEBUG
             raise e # Re-raise unexpected errors

        validated_data = serializer.validated_data
        model_name = validated_data['model']
        messages = validated_data['messages']
        stream = validated_data.get('stream', False)
        blueprint_params = validated_data.get('params', None)

        print_logger.debug(f"[ReqID: {request_id}] Validation passed. Checking model access for user {request.user} and model {model_name}") # DEBUG
        access_granted = await sync_to_async(validate_model_access)(request.user, model_name)
        if not access_granted:
             logger.warning(f"[ReqID: {request_id}] User {request.user} denied access to model '{model_name}'.")
             raise PermissionDenied(f"You do not have permission to access the model '{model_name}'.")

        print_logger.debug(f"[ReqID: {request_id}] Access granted. Getting blueprint instance for {model_name}") # DEBUG
        blueprint_instance = await get_blueprint_instance(model_name, params=blueprint_params)
        if blueprint_instance is None:
            logger.error(f"[ReqID: {request_id}] Blueprint '{model_name}' not found or failed to initialize (post-validation).")
            raise NotFound(f"The requested model (blueprint) '{model_name}' was not found or failed to initialize.")

        if stream: return await self._handle_streaming(blueprint_instance, messages, request_id, model_name)
        else: return await self._handle_non_streaming(blueprint_instance, messages, request_id, model_name)

# ==============================================================================
# Web UI Views (Django standard views)
# ==============================================================================
@login_required
def index(request):
    context = { 'user': request.user, 'available_blueprints': list(get_available_blueprints().keys()), }
    return render(request, 'swarm/index.html', context)

