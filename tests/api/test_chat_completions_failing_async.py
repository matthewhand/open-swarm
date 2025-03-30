import pytest
import asyncio
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock, AsyncMock
import json
# import sseclient # Manual parsing
from rest_framework import exceptions
from asgiref.sync import sync_to_async
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

async def async_gen_mock(data_to_yield):
    """Helper to create an async generator mock."""
    if isinstance(data_to_yield, Exception):
        logger.debug(f"async_gen_mock raising exception: {data_to_yield}")
        raise data_to_yield
    elif isinstance(data_to_yield, list):
        logger.debug(f"async_gen_mock yielding list: {data_to_yield}")
        for item in data_to_yield:
            yield item
            await asyncio.sleep(0.001)
    else:
        logger.debug(f"async_gen_mock yielding single item: {data_to_yield}")
        yield data_to_yield
        await asyncio.sleep(0.001)

@pytest.mark.django_db(transaction=True)
class TestChatCompletionsAPIFailingAsync:

    @pytest.fixture
    def client(self, async_client):
        return async_client

    @pytest.fixture
    async def authenticated_client(self, async_client, test_user):
        await sync_to_async(async_client.force_login)(test_user)
        return async_client

    @pytest.fixture(autouse=True)
    def setup_base_mocks(self, mocker, test_user):
        # General mocks - auth is assumed OK (session) for these streaming tests
        mocker.patch('swarm.auth.CustomSessionAuthentication.authenticate', return_value=(test_user, None))
        mocker.patch('swarm.auth.CustomTokenAuthentication.authenticate', return_value=None)
        mocker.patch('swarm.views.chat_views.validate_model_access', return_value=True)
        # Mock get_available_blueprints if needed elsewhere
        mocker.patch(
             'swarm.views.utils.get_available_blueprints',
             return_value={name: MagicMock() for name in ['echocraft', 'chatbot', 'error_bp']},
             create=True )

    # === Failing Async Streaming Tests ===
    @pytest.mark.asyncio
    async def test_echocraft_streaming_success(self, authenticated_client, mocker):
        url = reverse('chat_completions')
        data = {"model": "echocraft", "messages": [{"role": "user", "content": "Stream Test"}], "stream": True}

        # *** Define the async generator factory ***
        async def mock_sse_generator_factory(*args, **kwargs):
            logger.debug("mock_sse_generator for echocraft called")
            yield {"messages": [{"role": "assistant", "content": ""}]}; await asyncio.sleep(0.01)
            yield {"messages": [{"role": "assistant", "content": "Echo:"}]}; await asyncio.sleep(0.01)
            yield {"messages": [{"role": "assistant", "content": " Stream"}]}; await asyncio.sleep(0.01)
            yield {"messages": [{"role": "assistant", "content": " Test"}]}; await asyncio.sleep(0.01)
            logger.debug("mock_sse_generator for echocraft finished")

        # *** Create simple mock object for blueprint instance ***
        mock_bp = MagicMock()
        # *** Assign the AsyncMock directly to the run attribute ***
        mock_bp.run = AsyncMock(side_effect=mock_sse_generator_factory)

        # *** Patch get_blueprint_instance to return this specific mock ***
        mock_get_bp = mocker.patch('swarm.views.chat_views.get_blueprint_instance', new_callable=AsyncMock, return_value=mock_bp)

        response = await authenticated_client.post(url, json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.get('content-type') == 'text/event-stream'

        content_bytes = b''
        async for chunk in response.streaming_content:
            logger.debug(f"Received chunk: {chunk}")
            content_bytes += chunk
        raw_content = content_bytes.decode().strip()
        logger.debug(f"Raw SSE content:\n{raw_content}")

        if not raw_content: pytest.fail("Received empty streaming content")
        try:
             events_data = [line.replace('data: ', '', 1) for line in raw_content.split('\n\n') if line.startswith('data: ')]
             logger.debug(f"Parsed SSE data lines: {events_data}")
             done_event_present = '[DONE]' in events_data
             events = [json.loads(e) for e in events_data if e != '[DONE]']
        except Exception as e: pytest.fail(f"Failed to parse SSE events: {e}\nRaw Content:\n{raw_content}")

        assert len(events) > 0, "No valid SSE events found (excluding [DONE])"
        full_content = "".join(e['choices'][0]['delta'].get('content', '') for e in events if 'choices' in e and e['choices'])
        assert full_content == "Echo: Stream Test"
        assert done_event_present, "Did not receive [DONE] event"
        mock_get_bp.assert_awaited_once_with("echocraft", params=None)
        mock_bp.run.assert_awaited_once() # Check the mock on the specific instance

    @pytest.mark.asyncio
    async def test_chatbot_streaming_success(self, authenticated_client, mocker):
        url = reverse('chat_completions')
        data = {"model": "chatbot", "messages": [{"role": "user", "content": "Stream Chat"}], "stream": True}

        async def mock_sse_generator_factory(*args, **kwargs):
            logger.debug("mock_sse_generator for chatbot called")
            yield {"messages": [{"role": "assistant", "content": "Chatbot"}]}; await asyncio.sleep(0.01)
            yield {"messages": [{"role": "assistant", "content": " streaming!"}]}; await asyncio.sleep(0.01)
            logger.debug("mock_sse_generator for chatbot finished")

        mock_bp = MagicMock()
        mock_bp.run = AsyncMock(side_effect=mock_sse_generator_factory)
        mock_get_bp = mocker.patch('swarm.views.chat_views.get_blueprint_instance', new_callable=AsyncMock, return_value=mock_bp)

        response = await authenticated_client.post(url, json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.get('content-type') == 'text/event-stream'

        content_bytes = b''
        async for chunk in response.streaming_content:
             content_bytes += chunk
        raw_content = content_bytes.decode().strip()
        logger.debug(f"Raw SSE content:\n{raw_content}")

        if not raw_content: pytest.fail("Received empty streaming content")
        try:
             events_data = [line.replace('data: ', '', 1) for line in raw_content.strip().split('\n\n') if line.startswith('data: ')]
             logger.debug(f"Parsed SSE data lines: {events_data}")
             done_event_present = '[DONE]' in events_data
             events = [json.loads(e) for e in events_data if e != '[DONE]']
        except Exception as e: pytest.fail(f"Failed to parse SSE events: {e}\nRaw Content:\n{raw_content}")

        assert len(events) > 0, "No valid SSE events found (excluding [DONE])"
        full_content = "".join(e['choices'][0]['delta'].get('content', '') for e in events if 'choices' in e and e['choices'])
        assert full_content == "Chatbot streaming!"
        assert done_event_present, "Did not receive [DONE] event"
        mock_get_bp.assert_awaited_once_with("chatbot", params=None)
        mock_bp.run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_blueprint_run_exception_streaming_returns_error_sse(self, authenticated_client, mocker):
        url = reverse('chat_completions')
        data = {"model": "error_bp", "messages": [{"role": "user", "content": "Cause stream error"}], "stream": True}

        error_message = "Blueprint streaming runtime error"
        mock_bp = MagicMock()
        # *** Assign exception instance directly to run's side_effect ***
        mock_bp.run = AsyncMock(side_effect=Exception(error_message))
        mock_get_bp = mocker.patch('swarm.views.chat_views.get_blueprint_instance', new_callable=AsyncMock, return_value=mock_bp)


        response = await authenticated_client.post(url, json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        assert response.get('content-type') == 'text/event-stream'

        content_bytes = b''
        async for chunk in response.streaming_content:
            content_bytes += chunk
        raw_content = content_bytes.decode().strip()
        logger.debug(f"Raw SSE content (error case):\n{raw_content}")

        assert "internal_error" in raw_content, "SSE stream should contain an internal_error message"
        assert error_message in raw_content, "Specific error message not found in SSE stream"
        assert "[DONE]" in raw_content, "Stream should still end with [DONE] even after error"

        mock_get_bp.assert_awaited_once_with("error_bp", params=None)
        mock_bp.run.assert_awaited_once() # Check the mock on the specific instance
