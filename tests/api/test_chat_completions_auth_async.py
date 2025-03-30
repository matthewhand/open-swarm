import pytest
import asyncio
from django.urls import reverse
from rest_framework import status, exceptions
# Use async client provided by pytest-django
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
# *** Import AsyncMock ***
from unittest.mock import patch, MagicMock, AsyncMock
import json
from asgiref.sync import sync_to_async

User = get_user_model()

async def async_gen_mock(data_to_yield):
    """Helper to create an async generator mock."""
    if isinstance(data_to_yield, Exception):
        raise data_to_yield
    if isinstance(data_to_yield, list):
        for item in data_to_yield:
            yield item
            await asyncio.sleep(0.001)
    else:
        yield data_to_yield
        await asyncio.sleep(0.001)

@pytest.mark.django_db(transaction=True)
class TestChatCompletionsAuthAsync:

    @pytest.fixture
    def client(self, async_client):
         return async_client

    @pytest.fixture
    def mock_token_tuple(self, test_user):
        mock_token = MagicMock()
        mock_token.key = "mocktokenkey"
        mock_token.user = test_user
        return (test_user, mock_token)

    @pytest.fixture
    async def authenticated_client(self, async_client, test_user):
        await sync_to_async(async_client.force_login)(test_user)
        return async_client

    @pytest.fixture
    def token_client(self, async_client, mock_token_tuple):
         token_key = mock_token_tuple[1].key
         async_client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token_key}'
         yield async_client
         del async_client.defaults['HTTP_AUTHORIZATION']

    @pytest.fixture(autouse=True)
    def setup_common_mocks(self, mocker, test_user):
        self.test_user = test_user # Store for potential use in tests
        self.mock_blueprint_instance = MagicMock()
        # *** Use AsyncMock for the blueprint run method ***
        self.mock_blueprint_instance.run = AsyncMock(
            return_value=async_gen_mock([{"messages": [{"role": "assistant", "content": "Default Mock Response"}]}])
        )
        self.mock_blueprint_instance.get_llm_profile = MagicMock(return_value={"provider": "mock", "model": "mock-model"})
        self.mock_blueprint_instance.use_markdown = False

        # Mock get_blueprint_instance where it's used in the view (chat_views)
        self.mock_get_blueprint = mocker.patch(
            'swarm.views.chat_views.get_blueprint_instance',
            new_callable=AsyncMock, # Mock it as an async function
            return_value=self.mock_blueprint_instance
        )
        self.mock_get_available_blueprints = mocker.patch(
             'swarm.views.utils.get_available_blueprints', # Assuming called from index view?
             return_value={name: MagicMock() for name in ['echocraft', 'chatbot', 'error_bp', 'config_error_bp', 'nonexistent_bp']},
             create=True )
        # Mock validate_model_access (it's sync, called via sync_to_async in view)
        self.mock_validate_model_access = mocker.patch(
            'swarm.views.chat_views.validate_model_access', # Target where it's imported in the view
            return_value=True
        )

    # === Auth Tests (Use async client, mock sync auth methods) ===
    @pytest.mark.asyncio
    async def test_no_auth_returns_403(self, client, mocker, test_user):
        mocker.patch('swarm.auth.CustomSessionAuthentication.authenticate', return_value=None)
        mocker.patch('swarm.auth.CustomTokenAuthentication.authenticate', return_value=None)

        url = reverse('chat_completions')
        data = {"model": "echocraft", "messages": [{"role": "user", "content": "Hello"}]}
        response = await client.post(url, json.dumps(data), content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, client, mocker):
         mocker.patch('swarm.auth.CustomSessionAuthentication.authenticate', return_value=None)
         mocker.patch('swarm.auth.CustomTokenAuthentication.authenticate', side_effect=exceptions.AuthenticationFailed("Invalid token."))

         url = reverse('chat_completions')
         headers = {'HTTP_AUTHORIZATION': 'Bearer invalidtoken'}
         data = {"model": "echocraft", "messages": [{"role": "user", "content": "Hello"}]}
         response = await client.post(url, json.dumps(data), content_type='application/json', headers=headers)
         assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_valid_token_allows_access(self, token_client, mocker, test_user, mock_token_tuple):
         mocker.patch('swarm.auth.CustomSessionAuthentication.authenticate', return_value=None)
         mocker.patch('swarm.auth.CustomTokenAuthentication.authenticate', return_value=mock_token_tuple)

         url = reverse('chat_completions')
         data = {"model": "echocraft", "messages": [{"role": "user", "content": "Hello"}]}
         # Re-assign the run mock within the test if needed, or rely on the default setup
         self.mock_blueprint_instance.run = AsyncMock(return_value=async_gen_mock([{"messages": [{"role": "assistant", "content": "Echo: Hello"}]}]))

         response = await token_client.post(url, json.dumps(data), content_type='application/json')

         assert response.status_code == status.HTTP_200_OK
         response_data = json.loads(response.content.decode()) # Use response.content for async client
         assert response_data["choices"][0]["message"]["content"] == "Echo: Hello"

    @pytest.mark.asyncio
    async def test_valid_session_allows_access(self, authenticated_client, mocker, test_user):
         mocker.patch('swarm.auth.CustomSessionAuthentication.authenticate', return_value=(test_user, None))
         mocker.patch('swarm.auth.CustomTokenAuthentication.authenticate', return_value=None)

         url = reverse('chat_completions')
         data = {"model": "echocraft", "messages": [{"role": "user", "content": "Hello"}]}
         self.mock_blueprint_instance.run = AsyncMock(return_value=async_gen_mock([{"messages": [{"role": "assistant", "content": "Echo: Hello Session"}]}]))

         response = await authenticated_client.post(url, json.dumps(data), content_type='application/json')
         assert response.status_code == status.HTTP_200_OK
         response_data = json.loads(response.content.decode())
         assert response_data["choices"][0]["message"]["content"] == "Echo: Hello Session"

    # === Non-Streaming Success Tests (now async) ===
    @pytest.mark.asyncio
    async def test_echocraft_non_streaming_success(self, authenticated_client, mocker, test_user):
         mocker.patch('swarm.auth.CustomSessionAuthentication.authenticate', return_value=(test_user, None))
         mocker.patch('swarm.auth.CustomTokenAuthentication.authenticate', return_value=None)

         url = reverse('chat_completions')
         data = {"model": "echocraft", "messages": [{"role": "user", "content": "Hello Echo"}]}
         expected_content = "Echo: Hello Echo"
         self.mock_blueprint_instance.run = AsyncMock(return_value=async_gen_mock([{"messages": [{"role": "assistant", "content": expected_content}]}]))
         # Mock get_blueprint_instance directly to return the pre-configured mock blueprint
         mocker.patch('swarm.views.chat_views.get_blueprint_instance', new_callable=AsyncMock, return_value=self.mock_blueprint_instance)

         response = await authenticated_client.post(url, json.dumps(data), content_type='application/json')
         assert response.status_code == status.HTTP_200_OK
         response_data = json.loads(response.content.decode())
         assert response_data["choices"][0]["message"]["content"] == expected_content
         self.mock_get_blueprint.assert_awaited_once_with("echocraft", params=None)
         self.mock_blueprint_instance.run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_chatbot_non_streaming_success(self, authenticated_client, mocker, test_user):
        mocker.patch('swarm.auth.CustomSessionAuthentication.authenticate', return_value=(test_user, None))
        mocker.patch('swarm.auth.CustomTokenAuthentication.authenticate', return_value=None)

        url = reverse('chat_completions')
        data = {"model": "chatbot", "messages": [{"role": "user", "content": "Hi Chatbot"}]}
        expected_content = "Chatbot says hi!"
        self.mock_blueprint_instance.run = AsyncMock(return_value=async_gen_mock([{"messages": [{"role": "assistant", "content": expected_content}]}]))
        mocker.patch('swarm.views.chat_views.get_blueprint_instance', new_callable=AsyncMock, return_value=self.mock_blueprint_instance)

        response = await authenticated_client.post(url, json.dumps(data), content_type='application/json')
        assert response.status_code == status.HTTP_200_OK
        response_data = json.loads(response.content.decode())
        assert response_data["choices"][0]["message"]["content"] == expected_content
        self.mock_get_blueprint.assert_awaited_once_with("chatbot", params=None)
        self.mock_blueprint_instance.run.assert_awaited_once()
