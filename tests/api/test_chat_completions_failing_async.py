import pytest
import json
import asyncio
import time # Import time
from unittest.mock import AsyncMock, MagicMock
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import AsyncClient
# *** Import StreamingHttpResponse ***
from django.http import StreamingHttpResponse
from rest_framework import status, exceptions
from rest_framework.exceptions import APIException
from asgiref.sync import sync_to_async
# Import the view to patch its method
from swarm.views.chat_views import ChatCompletionsView

User = get_user_model()

# Helper to create SSE chunks
def create_sse_chunk(data: dict, request_id: str, model: str) -> str:
    chunk_data = {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": data, "logprobs": None, "finish_reason": None}]
    }
    return f"data: {json.dumps(chunk_data)}\n\n"

def create_sse_error(message: str, code: int = 500, type: str = "internal_error") -> str:
     error_chunk = {"error": {"message": message, "type": type, "code": code}}
     return f"data: {json.dumps(error_chunk)}\n\n"

# Async generator for mock streaming responses
async def mock_stream_generator(chunks: list):
    for chunk_str in chunks:
        yield chunk_str.encode('utf-8') # Encode to bytes for StreamingHttpResponse
        await asyncio.sleep(0.01) # Simulate delay
    yield b"data: [DONE]\n\n" # Encode to bytes


@pytest.mark.django_db(transaction=True)
class TestChatCompletionsAPIFailingAsync:

    @pytest.fixture
    def test_user(self, db):
        user = User.objects.create_user(username='testuser', password='password123')
        return user

    @pytest.fixture
    def async_client(self):
         return AsyncClient()

    @pytest.fixture
    async def authenticated_async_client(self, async_client, test_user):
         await sync_to_async(async_client.login)(username='testuser', password='password123')
         return async_client

    @pytest.fixture()
    def setup_general_mocks(self, mocker, test_user):
        mocker.patch('swarm.views.chat_views.validate_model_access', return_value=True)
        mocker.patch('swarm.auth.CustomSessionAuthentication.authenticate', return_value=(test_user, None))
        mocker.patch('swarm.auth.StaticTokenAuthentication.authenticate', return_value=None)
        mocker.patch('swarm.views.chat_views.get_blueprint_instance', new_callable=AsyncMock, return_value=MagicMock())


    @pytest.mark.asyncio
    async def test_echocraft_streaming_success(self, authenticated_async_client, mocker, setup_general_mocks):
        request_id = "test-stream-echo"
        model_name = "echocraft"
        chunks = [
            create_sse_chunk({"role": "assistant", "content": "Echo stream: Stream me"}, request_id, model_name)
        ]
        # *** Mock _handle_streaming directly ***
        mock_streaming_response = StreamingHttpResponse(
            mock_stream_generator(chunks), content_type="text/event-stream"
        )
        mocker.patch.object(ChatCompletionsView, '_handle_streaming', return_value=mock_streaming_response)

        url = reverse('chat_completions')
        data = {'model': model_name, 'messages': [{'role': 'user', 'content': 'Stream me'}], 'stream': True}
        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.get('content-type') == 'text/event-stream'

        content = b""
        async for chunk in response.streaming_content:
             content += chunk
        content_str = content.decode('utf-8')

        assert f'"id": "chatcmpl-{request_id}"' in content_str
        assert f'"model": "{model_name}"' in content_str
        assert '"delta": {"role": "assistant", "content": "Echo stream: Stream me"}' in content_str
        assert 'data: [DONE]' in content_str


    @pytest.mark.asyncio
    async def test_chatbot_streaming_success(self, authenticated_async_client, mocker, setup_general_mocks):
        request_id = "test-stream-chat"
        model_name = "chatbot"
        chunks = [
            create_sse_chunk({"role": "assistant", "content": "Chatbot"}, request_id, model_name),
            create_sse_chunk({"content": " stream"}, request_id, model_name),
            create_sse_chunk({"content": " response"}, request_id, model_name),
        ]
        mock_streaming_response = StreamingHttpResponse(
            mock_stream_generator(chunks), content_type="text/event-stream"
        )
        mocker.patch.object(ChatCompletionsView, '_handle_streaming', return_value=mock_streaming_response)

        url = reverse('chat_completions')
        data = {'model': model_name, 'messages': [{'role': 'user', 'content': 'Hi'}], 'stream': True}
        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.get('content-type') == 'text/event-stream'

        content = b""
        async for chunk in response.streaming_content:
             content += chunk
        content_str = content.decode('utf-8')

        assert content_str.count(f'"id": "chatcmpl-{request_id}"') == 3
        assert '"delta": {"role": "assistant", "content": "Chatbot"}' in content_str # Check first part of delta
        assert '"delta": {"content": " stream"}' in content_str
        assert '"delta": {"content": " response"}' in content_str
        assert 'data: [DONE]' in content_str


    @pytest.mark.asyncio
    async def test_blueprint_run_exception_streaming_returns_error_sse(self, authenticated_async_client, mocker, setup_general_mocks):
        error_message = "API error during stream: Blueprint failed!"
        error_code = status.HTTP_503_SERVICE_UNAVAILABLE
        chunks = [
            create_sse_error(error_message, code=error_code, type="api_error")
        ]
        mock_streaming_response = StreamingHttpResponse(
            mock_stream_generator(chunks), content_type="text/event-stream"
        )
        mocker.patch.object(ChatCompletionsView, '_handle_streaming', return_value=mock_streaming_response)

        mocker.patch('swarm.views.chat_views.get_blueprint_instance', new_callable=AsyncMock, return_value=MagicMock())

        url = reverse('chat_completions')
        data = {'model': 'error_bp', 'messages': [{'role': 'user', 'content': 'Cause error'}], 'stream': True}
        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.get('content-type') == 'text/event-stream'

        content = b""
        async for chunk in response.streaming_content:
             content += chunk
        content_str = content.decode('utf-8')

        assert 'data: {"error":' in content_str
        assert f'"message": "{error_message}"' in content_str
        assert f'"code": {error_code}' in content_str
        assert 'data: [DONE]' in content_str

