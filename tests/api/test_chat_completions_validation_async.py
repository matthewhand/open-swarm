import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import AsyncClient
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound, APIException, ValidationError
from asgiref.sync import sync_to_async
from swarm.views.chat_views import ChatCompletionsView
from swarm.permissions import HasValidTokenOrSession
from rest_framework.permissions import AllowAny
from swarm.serializers import ChatMessageSerializer

User = get_user_model()

async def mock_run_gen_validation(*args, **kwargs):
    yield {"messages": [{"role": "assistant", "content": "Default validation response"}]}

async def run_raises_runtime_error(*args, **kwargs):
    raise Exception("Runtime error in blueprint")
    yield

@pytest.mark.django_db(transaction=True)
class TestChatCompletionsValidationAsync:

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

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mocker, test_user):
        self.test_user = test_user
        self.mock_blueprint_instance = MagicMock()
        self.mock_blueprint_instance.run = mock_run_gen_validation

        self.mock_get_blueprint = mocker.patch(
            'swarm.views.chat_views.get_blueprint_instance',
            new_callable=AsyncMock,
            return_value=self.mock_blueprint_instance
        )
        self.mock_get_available_blueprints = mocker.patch(
             'swarm.views.utils.get_available_blueprints',
             return_value={name: MagicMock() for name in ['echocraft', 'chatbot', 'error_bp', 'config_error_bp']},
             create=True )
        self.mock_session_auth = mocker.patch(
             'swarm.auth.CustomSessionAuthentication.authenticate',
             return_value=(test_user, None)
        )
        self.mock_token_auth = mocker.patch(
             'swarm.auth.StaticTokenAuthentication.authenticate',
             return_value=None
        )
        self.mock_validate_access = mocker.patch(
             'swarm.views.chat_views.validate_model_access',
             return_value=True
        )
        mocker.patch.object(ChatCompletionsView, 'permission_classes', [AllowAny])


    # --- Validation Tests ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize("missing_field", ["model", "messages"])
    async def test_missing_required_field_returns_400(self, authenticated_async_client, missing_field):
        url = reverse('chat_completions')
        data = {'model': 'echocraft', 'messages': [{'role': 'user', 'content': 'test'}]}
        del data[missing_field]

        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert missing_field in response.json()
        assert 'This field is required.' in response.json()[missing_field][0]


    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_data, expected_error_key, expected_error_msg_part", [
        ({'model': 123, 'messages': []}, 'messages', 'Ensure this field has at least 1 elements'),
        ({'model': 'echocraft', 'messages': "not a list"}, 'messages', 'Expected a list of items'),
        ({'model': 'echocraft', 'messages': [{'role': 'user'}]}, 'messages', "This field is required."), # Content required error
        ({'model': 'echocraft', 'messages': [{'content': 'hi'}]}, 'messages', "This field is required."), # Role required error
        ({'model': 'echocraft', 'messages': [{'role': 'invalid', 'content': 'hi'}]}, 'messages', '"invalid" is not a valid choice'),
        # *** FIX: Match actual error message part from validate_messages ***
        ({'model': 'echocraft', 'messages': [{'role': 'user', 'content': 123}]}, 'messages', 'Content must be a string or null.'),
    ])
    async def test_invalid_field_type_or_content_returns_400(self, authenticated_async_client, invalid_data, expected_error_key, expected_error_msg_part):
        url = reverse('chat_completions')
        response = await authenticated_async_client.post(url, data=json.dumps(invalid_data), content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert expected_error_key in response_data, f"Key '{expected_error_key}' not in response: {response_data}"
        error_details = response_data[expected_error_key]

        assert expected_error_msg_part in str(error_details), \
               f"Expected error '{expected_error_msg_part}' not found in {error_details}"


    @pytest.mark.asyncio
    async def test_malformed_json_returns_400(self, authenticated_async_client):
        url = reverse('chat_completions')
        malformed_json = '{"model": "echocraft", "messages": [}'

        response = await authenticated_async_client.post(url, data=malformed_json, content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'JSON parse error' in response.json()['detail']


    # --- Permission/Not Found Tests ---

    @pytest.mark.asyncio
    async def test_nonexistent_model_permission_denied(self, authenticated_async_client, mocker):
        mocker.patch('swarm.views.chat_views.validate_model_access', return_value=False)

        url = reverse('chat_completions')
        data = {'model': 'restricted_bp', 'messages': [{'role': 'user', 'content': 'test'}]}
        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "You do not have permission to access the model 'restricted_bp'" in response.json()['detail']


    @pytest.mark.asyncio
    async def test_nonexistent_model_not_found(self, authenticated_async_client, mocker):
        async def get_bp_side_effect(name, params=None):
            if name == 'nonexistent_bp':
                return None
            else:
                instance = MagicMock()
                instance.run = mock_run_gen_validation
                return instance
        self.mock_get_blueprint.side_effect = get_bp_side_effect

        url = reverse('chat_completions')
        data = {'model': 'nonexistent_bp', 'messages': [{'role': 'user', 'content': 'test'}]}
        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "The requested model (blueprint) 'nonexistent_bp' was not found" in response.json()['detail']


    # --- Error Handling Tests ---

    @pytest.mark.asyncio
    async def test_blueprint_init_error_returns_500(self, authenticated_async_client, mocker):
        self.mock_get_blueprint.side_effect = ValueError("Failed to initialize blueprint")

        url = reverse('chat_completions')
        data = {'model': 'config_error_bp', 'messages': [{'role': 'user', 'content': 'test'}]}

        with pytest.raises(ValueError, match="Failed to initialize blueprint"):
             await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')


    @pytest.mark.asyncio
    async def test_blueprint_run_exception_non_streaming_returns_500(self, authenticated_async_client, mocker):
        self.mock_blueprint_instance.run = run_raises_runtime_error
        self.mock_get_blueprint.return_value = self.mock_blueprint_instance
        self.mock_get_blueprint.side_effect = None

        url = reverse('chat_completions')
        data = {'model': 'error_bp', 'messages': [{'role': 'user', 'content': 'Cause error'}], 'stream': False}
        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'Internal server error during generation' in response.json()['detail']

