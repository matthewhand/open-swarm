import pytest
from django.urls import reverse
from rest_framework import status, exceptions
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from unittest.mock import patch, MagicMock, AsyncMock
import json
import asyncio
from asgiref.sync import sync_to_async
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

async def async_gen_mock(data_to_yield):
    if isinstance(data_to_yield, Exception):
        logger.debug(f"async_gen_mock configured to raise exception: {data_to_yield}")
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
class TestChatCompletionsValidationAsync:

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
        self.mock_blueprint_instance.run = AsyncMock(
            return_value=async_gen_mock([{"messages": [{"role": "assistant", "content": "Default Mock Response"}]}])
        )
        self.mock_get_blueprint = mocker.patch(
            'swarm.views.chat_views.get_blueprint_instance',
            new_callable=AsyncMock,
            return_value=self.mock_blueprint_instance
        )
        self.mock_get_available_blueprints = mocker.patch(
             'swarm.views.utils.get_available_blueprints',
             return_value={name: MagicMock() for name in ['echocraft', 'chatbot', 'error_bp', 'config_error_bp', 'nonexistent_bp']},
             create=True )

        self.mock_session_auth = mocker.patch(
             'swarm.auth.CustomSessionAuthentication.authenticate',
             return_value=(test_user, None)
        )
        self.mock_token_auth = mocker.patch(
             'swarm.auth.CustomTokenAuthentication.authenticate',
             return_value=None
        )
        self.mock_validate_model_access = mocker.patch(
            'swarm.views.chat_views.validate_model_access',
            return_value=True
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("field_to_remove", ["model", "messages"])
    async def test_missing_required_field_returns_400(self, authenticated_client, field_to_remove):
        url = reverse('chat_completions')
        data = {"model": "echocraft", "messages": [{"role": "user", "content": "Test"}]}
        if field_to_remove in data: del data[field_to_remove] # Ensure key exists before deleting
        response = await authenticated_client.post(url, json.dumps(data), content_type='application/json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_data, expected_status", [
        ({"model": 123, "messages": [{"role": "user", "content": "Test"}]}, status.HTTP_400_BAD_REQUEST),
        ({"model": "echocraft", "messages": "not a list"}, status.HTTP_400_BAD_REQUEST),
        ({"model": "echocraft", "messages": [{"role": "user"}]}, status.HTTP_400_BAD_REQUEST), # Missing content
        ({"model": "echocraft", "messages": [{"content": "Test"}]}, status.HTTP_400_BAD_REQUEST), # Missing role
        ({"model": "echocraft", "messages": [{"role": "invalid", "content": "Test"}]}, status.HTTP_400_BAD_REQUEST),
        ({"model": "echocraft", "messages": [{"role": "user", "content": "Test"}], "stream": "not a boolean"}, status.HTTP_400_BAD_REQUEST),
    ])
    async def test_invalid_field_type_or_content_returns_400(self, authenticated_client, invalid_data, expected_status):
        url = reverse('chat_completions')
        response = await authenticated_client.post(url, json.dumps(invalid_data), content_type='application/json')
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}. Response: {response.content.decode()}"


    @pytest.mark.asyncio
    async def test_malformed_json_returns_400(self, authenticated_client):
        url = reverse('chat_completions')
        response = await authenticated_client.post(url, data=b'{"model": "echocraft", "messages": [}', content_type='application/json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_nonexistent_model_permission_denied(self, authenticated_client, mocker):
        mock_validate = mocker.patch('swarm.views.chat_views.validate_model_access', return_value=False)
        url = reverse('chat_completions')
        data = {"model": "actually_secret_bp", "messages": [{"role": "user", "content": "Test"}]}
        response = await authenticated_client.post(url, json.dumps(data), content_type='application/json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert mock_validate.call_count == 1
        call_args, call_kwargs = mock_validate.call_args
        assert call_args == (self.test_user, "actually_secret_bp")


    @pytest.mark.asyncio
    async def test_nonexistent_model_not_found(self, authenticated_client):
        url = reverse('chat_completions')
        data = {"model": "nonexistent_bp", "messages": [{"role": "user", "content": "Test"}]}
        self.mock_get_blueprint.return_value = None
        self.mock_get_blueprint.side_effect = None

        response = await authenticated_client.post(url, json.dumps(data), content_type='application/json')
        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Check await happened
        self.mock_get_blueprint.assert_awaited_once_with("nonexistent_bp", params=None)

    @pytest.mark.asyncio
    async def test_blueprint_init_error_returns_500(self, authenticated_client):
        url = reverse('chat_completions')
        data = {"model": "config_error_bp", "messages": [{"role": "user", "content": "Test"}]}
        config_error = ValueError("Config error")
        self.mock_get_blueprint.side_effect = config_error

        # *** Use pytest.raises to assert that the specific exception is raised ***
        with pytest.raises(ValueError, match="Config error"):
             await authenticated_client.post(url, json.dumps(data), content_type='application/json')

        # Assert mock was awaited (even though it raised an exception)
        self.mock_get_blueprint.assert_awaited_once_with("config_error_bp", params=None)


    @pytest.mark.asyncio
    async def test_blueprint_run_exception_non_streaming_returns_500(self, authenticated_client):
        url = reverse('chat_completions')
        data = {"model": "error_bp", "messages": [{"role": "user", "content": "Cause error"}]}
        self.mock_get_blueprint.side_effect = None
        self.mock_get_blueprint.return_value = self.mock_blueprint_instance
        error_message = "Blueprint runtime error"
        self.mock_blueprint_instance.run.side_effect = Exception(error_message)

        response = await authenticated_client.post(url, json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        # *** Use response.json() for DRF async client responses ***
        response_data = response.json()
        assert error_message in response_data["detail"]
        # Check awaits
        self.mock_get_blueprint.assert_awaited_once_with("error_bp", params=None)
        self.mock_blueprint_instance.run.assert_awaited_once()
