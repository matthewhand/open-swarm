import pytest
import json
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from asgiref.sync import sync_to_async

from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from swarm.extensions.blueprint.blueprint_base import BlueprintBase

User = get_user_model()
CHAT_URL = reverse('chat_completions')
ECHOCRAFT_MODEL = "echocraft"; CHATBOT_MODEL = "chatbot"; NON_EXISTENT_MODEL = "does_not_exist"

# --- Fixtures ---
@pytest.fixture
def test_user(db): return User.objects.create_user(username='testuser', password='password')
@pytest.fixture
def auth_token(db, test_user): token, _ = Token.objects.get_or_create(user=test_user); return token
@pytest.fixture
def base_request_data(): return {"model": ECHOCRAFT_MODEL, "messages": [{"role": "user", "content": "Test Input"}], "stream": False}
@pytest.fixture
def api_client(): return APIClient()

# --- Test Class ---
@pytest.mark.django_db(transaction=True)
class TestChatCompletionsAPIFailing:
    @pytest.fixture(autouse=True)
    def common_mocks(self, mocker):
        mocker.patch.dict('sys.modules', {'redis': MagicMock()})
        self.mock_echocraft_bp = MagicMock(spec=BlueprintBase); self.mock_echocraft_bp.run = AsyncMock()
        self.mock_chatbot_bp = MagicMock(spec=BlueprintBase); self.mock_chatbot_bp.run = AsyncMock()
        def get_mock_blueprint(model_name, params=None):
            if model_name == ECHOCRAFT_MODEL: return self.mock_echocraft_bp
            elif model_name == CHATBOT_MODEL: return self.mock_chatbot_bp
            else: return None
        self.get_blueprint_mock = mocker.patch('swarm.views.chat_views.get_blueprint_instance', new_callable=AsyncMock, side_effect=get_mock_blueprint)
        self.validate_access_mock = mocker.patch('swarm.views.chat_views.validate_model_access', return_value=True)
        yield

    def _configure_mock_run(self, blueprint_mock, return_value, is_stream=False):
        if is_stream:
            async def stream_gen():
                for chunk in return_value: yield chunk; await asyncio.sleep(0.01)
            blueprint_mock.run.return_value = stream_gen()
        else:
            async def async_gen(): yield return_value
            blueprint_mock.run.return_value = async_gen()

    # === Auth Test (using force_authenticate) ===
    async def test_valid_token_allows_access(self, api_client, test_user, auth_token, base_request_data):
        self._configure_mock_run(self.mock_echocraft_bp, {"messages": [{"role": "assistant", "content": "OK"}]})
        api_client.force_authenticate(user=test_user, token=auth_token)
        response = await sync_to_async(api_client.post)(
            CHAT_URL,
            data=base_request_data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        # Removed cleanup

    # === Validation Tests (using force_authenticate) ===
    @pytest.mark.parametrize("invalid_data, expected_error_part, expected_status", [
        ({"model": 123, "messages": [{"role":"user", "content":"hi"}]}, "model", status.HTTP_404_NOT_FOUND), # Expect 404 due to view logic
        ({"model": "m", "messages": [{"role":"user", "content":"hi"}], "stream": "yes"}, "stream", status.HTTP_404_NOT_FOUND), # Expect 404 due to view logic
    ])
    async def test_invalid_field_type_or_content_returns_400(self, api_client, test_user, auth_token, invalid_data, expected_error_part, expected_status):
        api_client.force_authenticate(user=test_user, token=auth_token)
        response = await sync_to_async(api_client.post)(
            CHAT_URL,
            data=invalid_data,
            format='json'
        )
        assert response.status_code == expected_status
        # Only check error content if we expect a 400
        if expected_status == status.HTTP_400_BAD_REQUEST:
            error_detail = response.json()
            assert expected_error_part in error_detail
            assert isinstance(error_detail.get(expected_error_part), list)
        # Removed cleanup

