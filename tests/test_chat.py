import os
import json
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth.models import User
from swarm.models import ChatConversation, ChatMessage
from swarm.auth import EnvOrTokenAuthentication
from swarm.extensions.blueprint.blueprint_base import BlueprintBase
# Import chat_views and utils separately
from swarm.views import chat_views, utils as view_utils # Keep this
from swarm.extensions.config import config_loader
from swarm.types import Response, Agent # Import Agent and Response

@pytest.fixture(scope="class")
def dummy_user_fixture(django_db_setup, django_db_blocker):
    """Create a dummy user accessible within the class, ensuring DB access."""
    with django_db_blocker.unblock():
        user, _ = User.objects.get_or_create(username="testuser", defaults={'is_active': True})
        if not user.has_usable_password():
            user.set_password("testpass")
            user.save()
        return user

@pytest.mark.django_db(transaction=True)
class TestChat:

    @pytest.fixture(autouse=True)
    def setup_method(self, monkeypatch, dummy_user_fixture):
        """Using pytest fixture for setup/teardown via monkeypatch."""
        self.client = APIClient()
        self.chat_url = reverse('chat_completions')
        self.dummy_user = dummy_user_fixture

        monkeypatch.setenv("ENABLE_API_AUTH", "True")
        monkeypatch.setenv("API_AUTH_TOKEN", "dummy-token")
        monkeypatch.setenv("STATEFUL_CHAT_ID_PATH", "metadata.conversationId || `null`")

        test_instance_self = self
        def mock_authenticate(auth_instance, request):
            auth_header = request.META.get("HTTP_AUTHORIZATION")
            token_expected = f"Bearer {os.environ.get('API_AUTH_TOKEN')}"
            if auth_header == token_expected:
                 return (test_instance_self.dummy_user, None)
            else:
                 return None
        monkeypatch.setattr(EnvOrTokenAuthentication, 'authenticate', mock_authenticate)

        # Create a valid Agent instance for the mock response
        self.mock_agent_instance = Agent(name="MockAgent", instructions="Test", mcp_servers=[])

        # Prepare mock response data using the Response type and the valid Agent
        self.mock_response_obj = Response(
             messages=[{"role": "assistant", "content": "Mocked response"}],
             agent=self.mock_agent_instance, # Use the actual Agent instance
             context_variables={"key": "value"}
        )
        self.mock_run_result = {
            "response": self.mock_response_obj,
            "context_variables": {"key": "updated_value"}
        }
        self.async_run_mock = AsyncMock(return_value=self.mock_run_result)

        # Define a simple DummyBlueprint for patching get_blueprint_instance
        class DummyBlueprint(BlueprintBase):
             metadata = {"title":"Dummy"}
             def __init__(self, config, **kwargs):
                  self.config = config
                  self.debug = kwargs.get('debug', False)
                  self.swarm = MagicMock()
                  self.swarm.agents = {"MockAgent": test_instance_self.mock_agent_instance}
                  self._discovered_tools = {}
                  self._discovered_resources = {}
                  self.starting_agent = test_instance_self.mock_agent_instance
                  self.context_variables = {}
                  # Patch the instance method HERE
                  self.run_with_context_async = test_instance_self.async_run_mock
             def create_agents(self): return {"MockAgent": test_instance_self.mock_agent_instance}
             def register_blueprint_urls(self): pass

        # Patch get_blueprint_instance in view_utils to return an *instance* of DummyBlueprint
        self.dummy_blueprint_instance = DummyBlueprint(config={"llm": {"default":{}}})
        monkeypatch.setattr(
             view_utils,
             'get_blueprint_instance',
             lambda model, context_vars: self.dummy_blueprint_instance
        )

        # Patch config access in chat_views and view_utils
        mock_config_data = {"llm": {"default": {"model": "mock-model"}}}
        monkeypatch.setattr(config_loader, 'config', mock_config_data, raising=False)
        monkeypatch.setattr(chat_views, 'view_utils', view_utils, raising=False)
        monkeypatch.setattr(view_utils, 'config', mock_config_data, raising=False)
        monkeypatch.setattr(view_utils, 'llm_config', mock_config_data.get('llm',{}), raising=False)


    def test_stateless_chat(self):
        """Test a basic stateless chat completion request."""
        # Removed incorrect patch context manager
        payload = { "model": "dummy_blueprint", "messages": [{"role": "user", "content": "Hello"}] }
        response = self.client.post(
            self.chat_url, data=json.dumps(payload), content_type="application/json",
            HTTP_AUTHORIZATION='Bearer dummy-token'
        )
        assert response.status_code == 200, f"Response content: {response.content.decode()}"
        response_data = response.json()
        assert "choices" in response_data and len(response_data["choices"]) > 0
        assert response_data["choices"][0]["message"]["content"] == self.mock_response_obj.messages[0]["content"]
        self.dummy_blueprint_instance.run_with_context_async.assert_called_once()


    def test_stateful_chat(self, monkeypatch):
        """Test a stateful chat using conversation_id."""
        # Removed incorrect patch context manager
        conversation_id = f"test-conv-{uuid.uuid4()}"
        mock_history_container = {'history': []}

        monkeypatch.setattr(view_utils, 'load_conversation_history',
                            lambda conv_id, current_msgs, tool_id=None: [m.copy() for m in mock_history_container['history']] + current_msgs)

        def mock_store(conv_id, history, response=None):
             current_history = [m.copy() for m in history]
             resp_msgs = []
             if response:
                  resp_data = response
                  if hasattr(resp_data, 'messages'): resp_msgs = resp_data.messages
                  elif isinstance(resp_data, dict) and 'messages' in resp_data: resp_msgs = resp_data['messages']
                  current_history.extend([m.copy() for m in resp_msgs])
             mock_history_container['history'] = current_history

        monkeypatch.setattr(view_utils, 'store_conversation_history', mock_store)

        # Turn 1
        payload_1 = { "model": "dummy_blueprint", "messages": [{"role": "user", "content": "First message"}], "metadata": {"conversationId": conversation_id} }
        response_1 = self.client.post( self.chat_url, data=json.dumps(payload_1), content_type="application/json", HTTP_AUTHORIZATION='Bearer dummy-token')
        assert response_1.status_code == 200
        assert self.dummy_blueprint_instance.run_with_context_async.call_count == 1
        call_args_1, _ = self.dummy_blueprint_instance.run_with_context_async.call_args
        messages_passed_1 = call_args_1[0]
        assert len(messages_passed_1) == 1, f"Expected 1 message passed, got {len(messages_passed_1)}"
        assert messages_passed_1[0]["content"] == "First message"
        assert len(mock_history_container['history']) == 2, f"Expected 2 messages in stored history, got {len(mock_history_container['history'])}"
        assert mock_history_container['history'][0]["content"] == "First message"
        assert mock_history_container['history'][1]["content"] == "Mocked response"

        self.dummy_blueprint_instance.run_with_context_async.reset_mock()

        # Turn 2
        payload_2 = { "model": "dummy_blueprint", "messages": [{"role": "user", "content": "Second message"}], "metadata": {"conversationId": conversation_id} }
        response_2 = self.client.post( self.chat_url, data=json.dumps(payload_2), content_type="application/json", HTTP_AUTHORIZATION='Bearer dummy-token')
        assert response_2.status_code == 200
        assert self.dummy_blueprint_instance.run_with_context_async.call_count == 1
        call_args_2, _ = self.dummy_blueprint_instance.run_with_context_async.call_args
        messages_passed_2 = call_args_2[0]
        assert len(messages_passed_2) == 3, f"Expected 3 messages passed, got {len(messages_passed_2)}"
        assert messages_passed_2[0]["content"] == "First message"
        assert messages_passed_2[1]["content"] == "Mocked response"
        assert messages_passed_2[2]["content"] == "Second message"
        assert len(mock_history_container['history']) == 4, f"Expected 4 messages in stored history, got {len(mock_history_container['history'])}"


    def test_invalid_input(self):
        """Test API response for invalid input (e.g., missing messages)."""
        payload = {"model": "dummy_blueprint"}
        response = self.client.post( self.chat_url, data=json.dumps(payload), content_type="application/json", HTTP_AUTHORIZATION='Bearer dummy-token')
        assert response.status_code == 400
        assert "'messages' field is required" in response.json().get("error", "")


    def test_jmespath_chat_id_extraction(self, monkeypatch):
        """Test chat ID extraction using JMESPath from metadata."""
        # Removed incorrect patch context manager
        monkeypatch.setenv("STATEFUL_CHAT_ID_PATH", "metadata.channelInfo.nested.conversationId || `null`")
        conversation_id = f"jmespath-test-{uuid.uuid4()}"
        payload = {
            "model": "dummy_blueprint",
            "messages": [{"role": "user", "content": "JMESPath test"}],
            "metadata": {"channelInfo": {"nested": {"conversationId": conversation_id}}}
        }
        mock_load = MagicMock()
        monkeypatch.setattr(view_utils, 'load_conversation_history', mock_load)
        monkeypatch.setattr(view_utils, 'store_conversation_history', MagicMock())

        response = self.client.post( self.chat_url, data=json.dumps(payload), content_type="application/json", HTTP_AUTHORIZATION='Bearer dummy-token')
        assert response.status_code == 200
        mock_load.assert_called_once()
        args, kwargs = mock_load.call_args
        assert args[0] == conversation_id
