import pytest
import asyncio
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
# *** Import AsyncMock ***
from unittest.mock import patch, MagicMock, AsyncMock
import json
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
    def setup_mocks(self, mocker, test_user):
        self.test_user = test_user
        self.mock_blueprint_instance = MagicMock()
        # Default run mock - assign AsyncMock directly here
        self.mock_blueprint_instance.run = AsyncMock(
             return_value=async_gen_mock([{"messages": [{"role": "assistant", "content": "Default Mock Response"}]}])
        )
        # Mock get_blueprint_instance where it's imported/used
        self.mock_get_blueprint = mocker.patch(
            'swarm.views.chat_views.get_blueprint_instance',
            new_callable=AsyncMock,
            return_value=self.mock_blueprint_instance
        )
        self.mock_get_available_blueprints = mocker.patch(
             'swarm.views.utils.get_available_blueprints', # Path might differ
             return_value={name: MagicMock() for name in ['echocraft', 'chatbot', 'error_bp', 'config_error_bp', 'nonexistent_bp']},
             create=True )
        # Mock sync auth methods (assuming session auth for authenticated client)
        mocker.patch('swarm.auth.CustomSessionAuthentication.authenticate', return_value=(test_user, None))
        mocker.patch('swarm.auth.CustomTokenAuthentication.authenticate', return_value=None)
        # Mock validate_model_access (assuming sync or wrapped in view)
        mocker.patch('swarm.views.chat_views.validate_model_access', return_value=True)

    # === Failing Async Streaming Tests ===
    @pytest.mark.asyncio
    async def test_echocraft_streaming_success(self, authenticated_client):
        url = reverse('chat_completions')
        data = {"model": "echocraft", "messages": [{"role": "user", "content": "Stream Test"}], "stream": True}

        # Create the generator instance first
        async def mock_sse_generator():
            logger.debug("mock_sse_generator for echocraft called")
            yield {"messages": [{"role": "assistant", "content": ""}]}; await asyncio.sleep(0.01)
            yield {"messages": [{"role": "assistant", "content": "Echo:"}]}; await asyncio.sleep(0.01)
            yield {"messages": [{"role": "assistant", "content": " Stream"}]}; await asyncio.sleep(0.01)
            yield {"messages": [{"role": "assistant", "content": " Test"}]}; await asyncio.sleep(0.01)
            logger.debug("mock_sse_generator for echocraft finished")

        # *** Set the return_value of the AsyncMock to the generator ***
        self.mock_blueprint_instance.run.return_value = mock_sse_generator()
        self.mock_get_blueprint.side_effect = None # Clear potential side_effect
        self.mock_get_blueprint.return_value = self.mock_blueprint_instance # Ensure get_blueprint returns the mock

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
        self.mock_get_blueprint.assert_awaited_once_with("echocraft", params=None)
        self.mock_blueprint_instance.run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_chatbot_streaming_success(self, authenticated_client):
        url = reverse('chat_completions')
        data = {"model": "chatbot", "messages": [{"role": "user", "content": "Stream Chat"}], "stream": True}

        async def mock_sse_generator():
            logger.debug("mock_sse_generator for chatbot called")
            yield {"messages": [{"role": "assistant", "content": "Chatbot"}]}; await asyncio.sleep(0.01)
            yield {"messages": [{"role": "assistant", "content": " streaming!"}]}; await asyncio.sleep(0.01)
            logger.debug("mock_sse_generator for chatbot finished")

        # *** Set the return_value of the AsyncMock to the generator ***
        self.mock_blueprint_instance.run.return_value = mock_sse_generator()
        self.mock_get_blueprint.side_effect = None
        self.mock_get_blueprint.return_value = self.mock_blueprint_instance

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
        self.mock_get_blueprint.assert_awaited_once_with("chatbot", params=None)
        self.mock_blueprint_instance.run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_blueprint_run_exception_streaming_returns_error_sse(self, authenticated_client):
        url = reverse('chat_completions')
        data = {"model": "error_bp", "messages": [{"role": "user", "content": "Cause stream error"}], "stream": True}

        error_message = "Blueprint streaming runtime error"
        # *** Assign exception instance directly to side_effect ***
        self.mock_blueprint_instance.run = AsyncMock(side_effect=Exception(error_message))
        self.mock_get_blueprint.side_effect = None
        self.mock_get_blueprint.return_value = self.mock_blueprint_instance

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

        self.mock_get_blueprint.assert_awaited_once_with("error_bp", params=None)
        self.mock_blueprint_instance.run.assert_awaited_once()
