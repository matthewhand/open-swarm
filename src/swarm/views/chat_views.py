import logging
import json
import uuid
import time
import asyncio # *** ADDED IMPORT ***
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
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound, APIException

from asgiref.sync import sync_to_async

from swarm.serializers import ChatCompletionRequestSerializer
from .utils import get_blueprint_instance, validate_model_access, get_available_blueprints
from swarm.permissions import HasValidTokenOrSession

logger = logging.getLogger(__name__)

# ==============================================================================
# API Views (DRF based)
# ==============================================================================

class HealthCheckView(APIView):
    """Simple health check endpoint."""
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        return Response({"status": "ok"})


class ChatCompletionsView(APIView):
    """
    APIView for handling OpenAI-compatible chat completions requests.
    """
    permission_classes = [HasValidTokenOrSession]

    async def _handle_non_streaming(self, blueprint_instance, messages: List[Dict[str, str]], request_id: str, model_name: str) -> Response:
        """Handles non-streaming chat completion requests."""
        logger.info(f"[ReqID: {request_id}] Processing non-streaming request for model '{model_name}'.")
        final_response_data = None
        start_time = time.time()

        try:
            async_generator = await blueprint_instance.run(messages)
            async for chunk in async_generator:
                if isinstance(chunk, dict) and "messages" in chunk:
                    final_response_data = chunk["messages"]
                    logger.debug(f"[ReqID: {request_id}] Received final data chunk: {final_response_data}")
                    break
                else:
                    logger.warning(f"[ReqID: {request_id}] Unexpected chunk format received in non-streaming mode: {chunk}")

            if not final_response_data:
                 logger.error(f"[ReqID: {request_id}] Blueprint '{model_name}' did not return valid data.")
                 raise APIException("Blueprint did not return valid data.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            response_payload = {
                "id": f"chatcmpl-{request_id}", "object": "chat.completion", "created": int(time.time()), "model": model_name,
                "choices": [{"index": 0, "message": final_response_data[0], "logprobs": None, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "system_fingerprint": None,
            }
            end_time = time.time()
            logger.info(f"[ReqID: {request_id}] Non-streaming request completed in {end_time - start_time:.2f}s.")
            return Response(response_payload, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[ReqID: {request_id}] Error during non-streaming blueprint execution: {e}", exc_info=True)
            if isinstance(e, TypeError) and ("__aiter__" in str(e) or "unexpected keyword argument" in str(e)):
                 logger.error(f"[ReqID: {request_id}] Blueprint run method signature or async usage mismatch. Check {type(blueprint_instance).__name__}.run()")
                 raise APIException(f"Internal server error: Blueprint signature/usage mismatch.", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e
            raise APIException(f"Internal server error during generation: {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e

    async def _handle_streaming(self, blueprint_instance, messages: List[Dict[str, str]], request_id: str, model_name: str) -> StreamingHttpResponse:
        """Handles streaming chat completion requests using Server-Sent Events (SSE)."""
        logger.info(f"[ReqID: {request_id}] Processing streaming request for model '{model_name}'.")

        async def event_stream():
            start_time = time.time()
            chunk_index = 0
            try:
                logger.debug(f"[ReqID: {request_id}] Awaiting blueprint run...")
                async_generator = await blueprint_instance.run(messages)
                logger.debug(f"[ReqID: {request_id}] Got async generator: {async_generator}. Starting iteration...")
                async for chunk in async_generator:
                    logger.debug(f"[ReqID: {request_id}] Received stream chunk {chunk_index}: {chunk}")
                    if not isinstance(chunk, dict) or "messages" not in chunk:
                         logger.warning(f"[ReqID: {request_id}] Skipping invalid chunk format: {chunk}")
                         continue

                    delta_content = chunk["messages"][0].get("content", "")
                    response_chunk = {
                        "id": f"chatcmpl-{request_id}", "object": "chat.completion.chunk", "created": int(time.time()), "model": model_name,
                        "choices": [{"index": 0, "delta": {"role": "assistant", "content": delta_content}, "logprobs": None, "finish_reason": None}]
                    }
                    logger.debug(f"[ReqID: {request_id}] Sending SSE chunk {chunk_index}")
                    yield f"data: {json.dumps(response_chunk)}\n\n"
                    chunk_index += 1
                    await asyncio.sleep(0.01) # Keep small sleep

                logger.debug(f"[ReqID: {request_id}] Finished iterating stream. Sending [DONE].")
                yield "data: [DONE]\n\n"
                end_time = time.time()
                logger.info(f"[ReqID: {request_id}] Streaming request completed in {end_time - start_time:.2f}s.")

            except Exception as e:
                logger.error(f"[ReqID: {request_id}] Error during streaming blueprint execution: {e}", exc_info=True)
                if isinstance(e, TypeError) and ("__aiter__" in str(e) or "unexpected keyword argument" in str(e)):
                    logger.error(f"[ReqID: {request_id}] Blueprint run method signature or async usage mismatch. Check {type(blueprint_instance).__name__}.run()")
                    error_msg = "Internal server error: Blueprint signature/usage mismatch."
                else:
                    error_msg = f"Internal server error during stream: {e}"
                error_chunk = {"error": {"message": error_msg, "type": "api_error"}}
                try:
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as send_err:
                     logger.error(f"[ReqID: {request_id}] Failed to send error chunk to client: {send_err}")

        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

    @method_decorator(csrf_exempt)
    async def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Manually dispatch to the appropriate async handler (post)."""
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers

        try:
            await sync_to_async(self.initial)(request, *args, **kwargs)
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed
            response = await handler(request, *args, **kwargs)
        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    async def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Handles POST requests for chat completions."""
        request_id = str(uuid.uuid4())
        logger.info(f"[ReqID: {request_id}] Received chat completion request.")

        try:
            request_data = json.loads(request.body)
            serializer = ChatCompletionRequestSerializer(data=request_data)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data
            model_name = validated_data['model']
            messages = validated_data['messages']
            stream = validated_data.get('stream', False)
            blueprint_params = validated_data.get('params', None)
        except json.JSONDecodeError:
             raise ValidationError("Invalid JSON body.")

        try:
            access_granted = await sync_to_async(validate_model_access)(request.user, model_name)
            if not access_granted:
                 logger.warning(f"[ReqID: {request_id}] User {request.user} denied access to model '{model_name}'.")
                 raise PermissionDenied(f"You do not have permission to access the model '{model_name}'.")
        except Exception as e:
             logger.error(f"[ReqID: {request_id}] Error during model access validation for '{model_name}': {e}", exc_info=True)
             raise APIException("Error checking model access.", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e

        try:
            blueprint_instance = await get_blueprint_instance(model_name, params=blueprint_params)
            if blueprint_instance is None:
                logger.error(f"[ReqID: {request_id}] Blueprint '{model_name}' not found or failed to initialize (post-validation).")
                raise NotFound(f"The requested model (blueprint) '{model_name}' was not found or failed to initialize.")
        except Exception as e:
            logger.error(f"[ReqID: {request_id}] Error getting blueprint instance '{model_name}': {e}", exc_info=True)
            raise APIException("Error loading the requested model.", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e

        try:
            if stream:
                return await self._handle_streaming(blueprint_instance, messages, request_id, model_name)
            else:
                return await self._handle_non_streaming(blueprint_instance, messages, request_id, model_name)
        except Exception as e:
             logger.error(f"[ReqID: {request_id}] Unexpected error during response handling for '{model_name}': {e}", exc_info=True)
             if not isinstance(e, APIException):
                  raise APIException("Internal server error during response generation.", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e
             else:
                  raise e

# ==============================================================================
# Web UI Views (Django standard views)
# ==============================================================================

@login_required
def index(request):
    """Renders the main Swarm Web UI page."""
    context = {
        'user': request.user,
        'available_blueprints': list(get_available_blueprints().keys()),
    }
    return render(request, 'swarm/index.html', context)

