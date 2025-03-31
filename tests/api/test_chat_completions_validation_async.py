
# --- Content for tests/api/test_chat_completions_validation_async.py ---
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import APIException, ParseError, ValidationError, PermissionDenied, NotFound

from swarm.views.chat_views import ChatCompletionsView
from swarm.auth import HasValidTokenOrSession # Assuming this exists now

# Use pytest-django fixtures for async client and settings
pytestmark = pytest.mark.django_db(transaction=True) # Ensure DB access and rollback

# Mock blueprint run generator
async def mock_run_gen(*args, **kwargs):
    # Simulate yielding the final result immediately for non-streaming tests
    yield {"messages": [{"role": "assistant", "content": "Mock Response"}]}

@pytest.fixture(scope="function")
def mock_get_blueprint_fixture():
    # Use AsyncMock for the top-level patch target if the view awaits it
    with patch('swarm.views.chat_views.get_blueprint_instance', new_callable=AsyncMock) as mock_get_bp:
        # Configure a default mock blueprint instance
        mock_blueprint_instance = MagicMock()
        # Make the run method an async generator mock
        async def _mock_run_async_gen(*args, **kwargs):
            yield {"messages": [{"role": "assistant", "content": "Mock Response"}]}
        mock_blueprint_instance.run = _mock_run_async_gen # Assign the async generator function
        mock_get_bp.return_value = mock_blueprint_instance
        yield mock_get_bp # Yield the mock itself for tests to manipulate

@pytest.mark.usefixtures("mock_get_blueprint_fixture")
class TestChatCompletionsValidationAsync:

    @pytest.fixture(autouse=True)
    def inject_mocks(self, mock_get_blueprint_fixture):
        """Injects the mock into the test class instance."""
        self.mock_get_blueprint = mock_get_blueprint_fixture

    # --- Test Cases ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize("field", ["model", "messages"])
    async def test_missing_required_field_returns_400(self, authenticated_async_client, field):
        url = reverse('chat_completions')
        data = {'model': 'test_model', 'messages': [{'role': 'user', 'content': 'test'}]}
        del data[field] # Remove the required field

        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert field in response_data # Check if the specific field error is reported

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_data, expected_error_part", [
        ({'model': 'test', 'messages': []}, "Ensure this field has at least 1 elements"), # Empty messages list
        ({'model': 'test', 'messages': "not a list"}, "Expected a list of items"), # Messages not a list
        ({'model': 'test'}, "This field is required."), # Missing messages entirely
        ({'messages': [{'role': 'user', 'content': 'test'}]}, "This field is required."), # Missing model
        ({'model': 'test', 'messages': [{'role': 'invalid', 'content': 'test'}]}, 'invalid" is not a valid choice'), # Invalid role
        ({'model': 'test', 'messages': [{'role': 'user', 'content': 123}]}, "Content must be a string or null."), # Invalid content type
    ])
    async def test_invalid_field_type_or_content_returns_400(self, authenticated_async_client, invalid_data, expected_error_part):
        url = reverse('chat_completions')
        response = await authenticated_async_client.post(url, data=json.dumps(invalid_data), content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()

        # Check if the core part of the expected error message is present anywhere
        # in the string representation of the response JSON.
        core_expected_error = expected_error_part.strip('\'". ')
        error_found = any(core_expected_error in str(value) for value in response_data.values())

        assert error_found, f"Expected error containing '{core_expected_error}' (from '{expected_error_part}') not found in response: {response_data}"


    @pytest.mark.asyncio
    async def test_malformed_json_returns_400(self, authenticated_async_client):
        url = reverse('chat_completions')
        malformed_json = '{"model": "test", "messages": [{"role": "user", "content": "test"]' # Missing closing brace

        response = await authenticated_async_client.post(url, data=malformed_json, content_type='application/json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "JSON parse error" in response.json().get("detail", "")

    @pytest.mark.asyncio
    async def test_nonexistent_model_permission_denied(self, authenticated_async_client, mocker):
        # Mock validate_model_access where it's *used* in the view to return False
        mocker.patch('swarm.views.chat_views.validate_model_access', return_value=False)

        url = reverse('chat_completions')
        data = {'model': 'nonexistent_model', 'messages': [{'role': 'user', 'content': 'test'}]}

        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission to access the model 'nonexistent_model'" in response.json().get("detail", "")

    @pytest.mark.asyncio
    async def test_nonexistent_model_not_found(self, authenticated_async_client, mocker):
         # Ensure permission check passes by mocking where it's used
         mocker.patch('swarm.views.chat_views.validate_model_access', return_value=True)

         # Mock get_blueprint_instance to return None (as it's awaited in the view)
         self.mock_get_blueprint.return_value = None

         url = reverse('chat_completions')
         data = {'model': 'not_found_model', 'messages': [{'role': 'user', 'content': 'test'}]}

         response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

         assert response.status_code == status.HTTP_404_NOT_FOUND
         assert "model (blueprint) 'not_found_model' was not found" in response.json().get("detail", "")


    @pytest.mark.asyncio
    async def test_blueprint_init_error_returns_500(self, authenticated_async_client, mocker):
        # Ensure permission check passes for the target model
        mocker.patch('swarm.views.chat_views.validate_model_access', return_value=True)

        # Mock get_blueprint_instance to raise an exception simulating init failure
        mock_get_bp = mocker.patch('swarm.views.chat_views.get_blueprint_instance', new_callable=AsyncMock)
        mock_get_bp.side_effect = ValueError("Failed to initialize blueprint")

        url = reverse('chat_completions')
        data = {'model': 'config_error_bp', 'messages': [{'role': 'user', 'content': 'test'}]}

        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        response_data = response.json()
        assert "Failed to load model 'config_error_bp'" in response_data.get("detail", "")
        assert "Failed to initialize blueprint" in response_data.get("detail", "")


    @pytest.mark.asyncio
    async def test_blueprint_run_exception_non_streaming_returns_500(self, authenticated_async_client, mocker):
        # Ensure permission check passes for the target model
        mocker.patch('swarm.views.chat_views.validate_model_access', return_value=True)

        # Mock the blueprint's run method to raise an exception
        mock_blueprint_instance = MagicMock()
        # Ensure the run mock is an async function/generator that raises
        async def failing_run(*args, **kwargs):
            raise RuntimeError("Blueprint execution failed")
            yield # Need yield to make it an async generator if the view expects one
        mock_blueprint_instance.run = failing_run # Assign the async function directly
        # Ensure the mock_get_blueprint fixture returns this instance
        self.mock_get_blueprint.return_value = mock_blueprint_instance

        url = reverse('chat_completions')
        data = {'model': 'runtime_error_bp', 'messages': [{'role': 'user', 'content': 'test'}]}

        response = await authenticated_async_client.post(url, data=json.dumps(data), content_type='application/json')

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        response_data = response.json()
        assert "Internal server error during generation" in response_data.get("detail", "")
        assert "Blueprint execution failed" in response_data.get("detail", "")
