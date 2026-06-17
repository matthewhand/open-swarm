"""OpenAI Responses API (`/v1/responses`) — MVP implementation.

This view accepts an OpenAI Responses-style request, normalizes its ``input``
(string OR array of input items / messages) plus optional ``instructions`` into
a standard chat ``messages`` list, then runs it through the SAME
blueprint-resolution + run machinery that
:class:`swarm.views.chat_views.ChatCompletionsView` uses.

The response is shaped like an OpenAI ``response`` object (``output`` items +
flattened ``output_text``). Streaming is supported via the existing SSE machinery
and emits ``response.output_text.delta`` events.
"""
import asyncio
import json
import logging
import sys
import time
import uuid
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponseBase,
    StreamingHttpResponse,
)
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    ParseError,
    PermissionDenied,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from swarm.core import responses_store

from .chat_views import _chunk_is_final, _extract_message_from_chunk
from .openai_schema import responses_schema
from .utils import get_blueprint_instance, validate_model_access

logger = logging.getLogger(__name__)
print_logger = logging.getLogger('print_debug')

# Bridge module aliasing between 'swarm' and 'src.swarm' so test patches hit the
# correct module (mirrors chat_views.py).
try:
    if __name__ == 'swarm.views.responses_views':
        sys.modules.setdefault('src.swarm.views.responses_views', sys.modules[__name__])
    elif __name__ == 'src.swarm.views.responses_views':
        sys.modules.setdefault('swarm.views.responses_views', sys.modules[__name__])
except Exception:
    pass


def _normalize_input_to_messages(
    input_value: Any,
    instructions: str | None = None,
) -> list[dict[str, str]]:
    """Normalize a Responses-style ``input`` into a chat ``messages`` list.

    - ``input`` as a string -> a single ``user`` message.
    - ``input`` as an array of ``{role, content}`` items -> passthrough, with
      content coerced to a string (Responses items may carry content as a list
      of parts such as ``[{"type": "input_text", "text": "..."}]``).
    - ``instructions`` (if given) is prepended as a ``system`` message.
    """
    messages: list[dict[str, str]] = []
    if instructions:
        messages.append({"role": "system", "content": str(instructions)})

    if isinstance(input_value, str):
        messages.append({"role": "user", "content": input_value})
        return messages

    if isinstance(input_value, list):
        for item in input_value:
            if not isinstance(item, dict):
                # Bare string entries are treated as user content.
                messages.append({"role": "user", "content": str(item)})
                continue
            role = item.get("role") or "user"
            content = item.get("content")
            messages.append({"role": role, "content": _coerce_content(content)})
        return messages

    raise ParseError("'input' must be a string or an array of input items.")


def _coerce_content(content: Any) -> str:
    """Coerce Responses content (string, or list of content parts) to a string."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts)
    return str(content)


async def _async_auth_dispatch(view: APIView, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
    """Shared async dispatch (mirrors ChatCompletionsView): authenticate, enforce
    ``ENABLE_API_AUTH``, run the (async or sync) handler, finalize."""
    view.args = args
    view.kwargs = kwargs
    drf_request: Request = view.initialize_request(request, *args, **kwargs)
    view.request = drf_request
    view.headers = view.default_response_headers

    response = None
    try:
        await sync_to_async(view.perform_authentication)(drf_request)

        if bool(getattr(settings, 'ENABLE_API_AUTH', False)):
            has_token = getattr(drf_request, 'auth', None) is not None
            user_obj = getattr(drf_request, 'user', None)
            is_authenticated = bool(user_obj and getattr(user_obj, 'is_authenticated', False))
            if not (has_token or is_authenticated):
                raise PermissionDenied('Authentication credentials were not provided')

        view.check_permissions(drf_request)
        view.check_throttles(drf_request)

        method = drf_request.method.lower()
        handler = getattr(view, method, view.http_method_not_allowed) if method in view.http_method_names else view.http_method_not_allowed

        if asyncio.iscoroutinefunction(handler):
            response = await handler(drf_request, *args, **kwargs)
        else:
            response = await sync_to_async(handler)(drf_request, *args, **kwargs)
    except Exception as exc:
        response = view.handle_exception(exc)

    view.response = view.finalize_response(drf_request, response, *args, **kwargs)
    return view.response


class ResponsesView(APIView):
    """Handles OpenAI Responses API requests (``/v1/responses``).

    Reuses ``ChatCompletionsView``'s blueprint-resolution + run path. Stateful:
    a response is persisted (unless ``store: false``) and ``previous_response_id``
    continues a prior conversation. See :mod:`swarm.core.responses_store`.
    """

    @method_decorator(csrf_exempt)
    async def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        return await _async_auth_dispatch(self, request, *args, **kwargs)

    @responses_schema
    async def post(self, request: Request, *_args: Any, **_kwargs: Any) -> HttpResponseBase:
        request_id = str(uuid.uuid4())
        logger.info(f"[ReqID: {request_id}] Processing /v1/responses POST request.")

        # --- Request body parsing ---
        try:
            request_data = request.data
        except ParseError as e:
            logger.error(f"[ReqID: {request_id}] Invalid request body format: {e.detail}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"[ReqID: {request_id}] JSON Decode Error: {e}")
            raise ParseError(f"Invalid JSON body: {e}") from e

        if not isinstance(request_data, dict):
            raise ParseError("Request body must be a JSON object.")

        model_name = request_data.get('model')
        if not model_name or not isinstance(model_name, str):
            raise ParseError("Field 'model' is required and must be a string.")

        if 'input' not in request_data:
            raise ParseError("Field 'input' is required.")

        stream = bool(request_data.get('stream', False))
        instructions = request_data.get('instructions')
        previous_response_id = request_data.get('previous_response_id')
        store = request_data.get('store', True) is not False  # persist unless store:false

        messages = _normalize_input_to_messages(request_data.get('input'), instructions)
        if not messages:
            raise ParseError("'input' did not yield any messages.")

        # --- Statefulness: continue a prior conversation by id ---
        if previous_response_id:
            prior = await sync_to_async(responses_store.load)(str(previous_response_id))
            if prior is None:
                raise NotFound(f"Previous response '{previous_response_id}' not found.")
            messages = list(prior.get("messages") or []) + messages

        # --- Model access validation (same helper as ChatCompletionsView) ---
        try:
            access_granted = await sync_to_async(validate_model_access)(request.user, model_name)
        except Exception as e:
            logger.error(f"[ReqID: {request_id}] Error during model access validation for '{model_name}': {e}", exc_info=True)
            raise APIException("Error checking model permissions.", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e

        # --- Get blueprint instance (existence determines 404) ---
        try:
            blueprint_instance = await get_blueprint_instance(model_name, params=None)
        except Exception as e:
            logger.error(f"[ReqID: {request_id}] Error getting blueprint instance for '{model_name}': {e}", exc_info=True)
            raise APIException(f"Failed to load model '{model_name}': {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e

        if blueprint_instance is None:
            logger.error(f"[ReqID: {request_id}] Blueprint '{model_name}' not found or failed to initialize.")
            raise NotFound(f"The requested model (blueprint) '{model_name}' was not found or could not be initialized.")

        if not access_granted:
            logger.warning(f"[ReqID: {request_id}] User '{request.user}' denied access to model '{model_name}'.")
            raise PermissionDenied(f"You do not have permission to access the model '{model_name}'.")

        if stream:
            return await self._handle_streaming(blueprint_instance, messages, request_id, model_name, store, previous_response_id)
        return await self._handle_non_streaming(blueprint_instance, messages, request_id, model_name, store, previous_response_id)

    async def _handle_non_streaming(self, blueprint_instance, messages, request_id, model_name, store=True, previous_response_id=None) -> Response:
        """Consume the blueprint generator, keep the last message, shape a response object."""
        final_message = None
        try:
            async_generator = blueprint_instance.run(messages, stream=False)
            async for chunk in async_generator:
                message = _extract_message_from_chunk(chunk)
                if message is None:
                    continue
                final_message = message
                if _chunk_is_final(chunk):
                    break

            if not isinstance(final_message, dict) or final_message.get('content') is None:
                logger.error(f"[ReqID: {request_id}] Blueprint '{model_name}' did not yield any valid message chunk.")
                raise APIException("Blueprint did not return valid data.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            answer = final_message['content']
        except APIException:
            raise
        except Exception as e:
            logger.error(f"[ReqID: {request_id}] Unexpected error during /v1/responses generation: {e}", exc_info=True)
            raise APIException(f"Internal server error during generation: {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR) from e

        payload = _build_response_payload(request_id, model_name, answer, previous_response_id)
        if store:
            await sync_to_async(_persist)(payload, messages, answer)
        return Response(payload, status=status.HTTP_200_OK)

    async def _handle_streaming(self, blueprint_instance, messages, request_id, model_name, store=True, previous_response_id=None) -> StreamingHttpResponse:
        """Stream ``response.output_text.delta`` SSE events, then a final completed response."""
        response_id = f"resp_{request_id}"

        async def event_stream():
            full_text_parts: list[str] = []
            try:
                async_generator = blueprint_instance.run(messages, stream=True)
                async for chunk in async_generator:
                    message = _extract_message_from_chunk(chunk)
                    if message is None:
                        continue
                    delta = message.get("content")
                    if not delta:
                        continue
                    full_text_parts.append(delta)
                    event = {
                        "type": "response.output_text.delta",
                        "response_id": response_id,
                        "delta": delta,
                    }
                    yield f"data: {json.dumps(event)}\n\n"
                    await asyncio.sleep(0.01)

                final_text = "".join(full_text_parts)
                payload = _build_response_payload(request_id, model_name, final_text, previous_response_id)
                if store:
                    await sync_to_async(_persist)(payload, messages, final_text)
                completed = {"type": "response.completed", "response": payload}
                yield f"data: {json.dumps(completed)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"[ReqID: {request_id}] Error during /v1/responses streaming: {e}", exc_info=True)
                error_event = {"type": "error", "error": {"message": str(e)}}
                yield f"data: {json.dumps(error_event)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


def _build_response_payload(
    request_id: str, model_name: str, answer: str, previous_response_id: str | None = None
) -> dict[str, Any]:
    """Shape an OpenAI Responses-style ``response`` object."""
    return {
        "id": f"resp_{request_id}",
        "object": "response",
        "created_at": int(time.time()),
        "model": model_name,
        "status": "completed",
        "previous_response_id": previous_response_id,
        "output": [
            {
                "type": "message",
                "id": f"msg_{request_id}",
                "role": "assistant",
                "content": [{"type": "output_text", "text": answer}],
            }
        ],
        "output_text": answer,
        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    }


def _persist(payload: dict[str, Any], messages: list[dict[str, Any]], answer: str) -> None:
    """Save a response record so it can be retrieved and chained from later."""
    record = {
        "id": payload["id"],
        "object": "response",
        "response": payload,
        # Full transcript incl. the assistant reply, so previous_response_id replays it.
        "messages": list(messages) + [{"role": "assistant", "content": answer}],
    }
    responses_store.save(record)


class ResponsesDetailView(APIView):
    """Retrieve or delete a stored response (``/v1/responses/<id>``)."""

    @method_decorator(csrf_exempt)
    async def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        return await _async_auth_dispatch(self, request, *args, **kwargs)

    async def get(self, _request: Request, response_id: str, *_a: Any, **_k: Any) -> Response:
        record = await sync_to_async(responses_store.load)(response_id)
        if record is None:
            raise NotFound(f"Response '{response_id}' not found.")
        return Response(record.get("response") or record, status=status.HTTP_200_OK)

    async def delete(self, _request: Request, response_id: str, *_a: Any, **_k: Any) -> Response:
        deleted = await sync_to_async(responses_store.delete)(response_id)
        if not deleted:
            raise NotFound(f"Response '{response_id}' not found.")
        return Response({"id": response_id, "object": "response.deleted", "deleted": True}, status=status.HTTP_200_OK)
