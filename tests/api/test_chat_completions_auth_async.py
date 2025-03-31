import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status, exceptions
from rest_framework.permissions import IsAuthenticated, AllowAny
from asgiref.sync import sync_to_async
from swarm.views.chat_views import ChatCompletionsView
from swarm.permissions import HasValidTokenOrSession

User = get_user_model()

# --- FIX: Modify mock generator output ---
async def mock_run_gen(*args, **kwargs):
    messages = args[0] if args else []
    last_user_msg = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), "no input")
    # Yield the structure expected by _handle_non_streaming (dict with 'messages' key)
    yield {"messages": [{"role": "assistant", "content": f"Echo: {last_user_msg}"}]}
# --- End FIX ---

@pytest.mark.django_db(transaction=True)
class TestChatCompletionsAuthAsync:

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mocker, test_user): # test_user now comes from conftest
        self.test_user = test_user
        self.mock_blueprint_instance = MagicMock()
        # --- FIX: Ensure the mock instance uses the corrected generator ---
        self.mock_blueprint_instance.run = mock_run_gen
        # --- End FIX ---

        self.mock_get_blueprint = mocker.patch(
            'swarm.views.chat_views.get_blueprint_instance',
            new_callable=AsyncMock,
            return_value=self.mock_blueprint_instance
        )
        self.mock_validate_access = mocker.patch(
             'swarm.views.chat_views.validate_model_access',
             return_value=True
        )


    @pytest.mark.asyncio
    async def test_no_auth_returns_403(self, async_client, mocker, test_user, settings): # async_client from conftest
        settings.ENABLE_API_AUTH = True
        # Ensure SWARM_API_KEY is set if ENABLE_API_AUTH is True, even if not used for the specific auth path being tested
        settings.SWARM_API_KEY = "a_valid_key_must_be_set_for_auth_to_be_enabled"

        mocker.patch('swarm.auth.CustomSessionAuthentication.authenticate', return_value=None)
        mocker.patch('swarm.auth.StaticTokenAuthentication.authenticate', return_value=None)
        mocker.patch.object(ChatCompletionsView, 'permission_classes', [HasValidTokenOrSession])

        url = reverse('chat_completions')
        data = {'model': 'echocraft', 'messages': [{'role': 'user', 'content': 'test'}]}
        response = await async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'Authentication credentials were not provided' in response.json()['detail']


    @pytest.mark.asyncio
    async def test_invalid_token_returns_403(self, async_client, mocker, settings): # async_client from conftest
        settings.ENABLE_API_AUTH = True
        settings.SWARM_API_KEY = "correct_key"

        mocker.patch('swarm.auth.CustomSessionAuthentication.authenticate', return_value=None)
        mocker.patch('swarm.auth.StaticTokenAuthentication.authenticate', return_value=None)
        mocker.patch.object(ChatCompletionsView, 'permission_classes', [HasValidTokenOrSession])


        url = reverse('chat_completions')
        data = {'model': 'echocraft', 'messages': [{'role': 'user', 'content': 'test'}]}
        headers = {'HTTP_AUTHORIZATION': 'Bearer invalid_token'}
        response = await async_client.post(url, data=json.dumps(data), content_type='application/json', **headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'Authentication credentials were not provided' in response.json()['detail'] or \
               'Invalid API Key' in response.json()['detail']


    @pytest.mark.asyncio
    async def test_valid_token_allows_access(self, async_client, mocker, test_user, settings): # async_client from conftest
        settings.ENABLE_API_AUTH = True
        settings.SWARM_API_KEY = "valid_api_key"

        mocker.patch('swarm.auth.CustomSessionAuthentication.authenticate', return_value=None)
        mocker.patch('swarm.auth.StaticTokenAuthentication.authenticate', return_value=(test_user, settings.SWARM_API_KEY))
        mocker.patch.object(ChatCompletionsView, 'permission_classes', [HasValidTokenOrSession])

        # Mocks are handled by autouse fixture

        url = reverse('chat_completions')
        data = {'model': 'echocraft', 'messages': [{'role': 'user', 'content': 'test'}]}
        headers = {'HTTP_AUTHORIZATION': f'Bearer {settings.SWARM_API_KEY}'}
        response = await async_client.post(url, data=json.dumps(data), content_type='application/json', **headers)

        assert response.status_code == status.HTTP_200_OK
        # --- FIX: Adjust assertion for the actual content ---
        assert 'Echo: test' in response.json()['choices'][0]['message']['content']
        # --- End FIX ---


    @pytest.mark.asyncio
    async def test_valid_session_allows_access(self, authenticated_async_client, mocker, test_user, settings): # authenticated_async_client from conftest
        settings.ENABLE_API_AUTH = True
        settings.SWARM_API_KEY = "some_key_or_none"

        mocker.patch('swarm.auth.StaticTokenAuthentication.authenticate', return_value=None)
        mocker.patch.object(ChatCompletionsView, 'permission_classes', [HasValidTokenOrSession])

        # Mocks are handled by autouse fixture

        url = reverse('chat_completions')
        data = {'model': 'echocraft', 'messages': [{'role': 'user', 'content': 'session test'}]}
        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        # --- FIX: Adjust assertion for the actual content ---
        assert 'Echo: session test' in response.json()['choices'][0]['message']['content']
        # --- End FIX ---


    @pytest.mark.asyncio
    async def test_echocraft_non_streaming_success_auth_disabled(self, authenticated_async_client, mocker, test_user, settings): # Renamed for clarity
        settings.ENABLE_API_AUTH = False

        mocker.patch.object(ChatCompletionsView, 'permission_classes', [AllowAny])

        # Mocks are handled by autouse fixture

        url = reverse('chat_completions')
        data = {'model': 'echocraft', 'messages': [{'role': 'user', 'content': 'Hello EchoCraft'}]}
        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['model'] == 'echocraft'
        # --- FIX: Adjust assertion for the actual content ---
        assert response_data['choices'][0]['message']['content'] == 'Echo: Hello EchoCraft'
        # --- End FIX ---


    @pytest.mark.asyncio
    async def test_chatbot_non_streaming_success_auth_disabled(self, authenticated_async_client, mocker, test_user, settings): # Renamed for clarity
        settings.ENABLE_API_AUTH = False

        mocker.patch.object(ChatCompletionsView, 'permission_classes', [AllowAny])

        # --- FIX: Modify mock generator output ---
        async def chatbot_run_gen(*args, **kwargs):
             yield {"messages": [{"role": "assistant", "content": "Chatbot Response"}]}
        # --- End FIX ---

        mock_chatbot_instance = MagicMock()
        mock_chatbot_instance.run = chatbot_run_gen

        # Override the autouse mock_get_blueprint for this specific test
        mocker.patch(
            'swarm.views.chat_views.get_blueprint_instance',
            new_callable=AsyncMock,
            return_value=mock_chatbot_instance
        )

        url = reverse('chat_completions')
        data = {'model': 'chatbot', 'messages': [{'role': 'user', 'content': 'Hi Chatbot'}]}
        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data['model'] == 'chatbot'
        # --- FIX: Adjust assertion for the actual content ---
        assert response_data['choices'][0]['message']['content'] == 'Chatbot Response'
        # --- End FIX ---

