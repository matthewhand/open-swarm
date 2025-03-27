import json
import uuid
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
import asyncio

from swarm.extensions.blueprint.blueprint_base import BlueprintBase
from swarm.types import Agent, Response, ChatMessage
from swarm.views import utils as view_utils

# Dummy Blueprint for testing
class DummyBlueprint(BlueprintBase):
    def __init__(self, *args, **kwargs):
        self._metadata = {"title": "Dummy", "description": "Test"}
        self.swarm = MagicMock()
        self.run_with_context_async = AsyncMock(
            return_value={ "response": Response(messages=[ChatMessage(role="assistant", content="Mocked response")]), "context_variables": {"active_agent_name": "DummyAgent"} }
        )
        self.config = kwargs.get('config', {}); self.debug = kwargs.get('debug', False)
        self.context_variables = {"active_agent_name": "DummyAgent"}
    @property
    def metadata(self): return self._metadata
    def create_agents(self):
        agent = Agent(name="DummyAgent"); self.starting_agent = agent
        self.swarm.agents = {"DummyAgent": agent}; return self.swarm.agents

mock_history_container = {'history': []}
def mock_store(conv_id, history, response=None):
     global mock_history_container; current_history = []
     for msg in history:
         if hasattr(msg, 'model_dump'): current_history.append(msg.model_dump(exclude_none=True))
         elif isinstance(msg, dict): current_history.append(msg.copy())
         else: current_history.append(msg)
     resp_msgs = [];
     if response:
          resp_data = response; raw_resp_msgs = []
          if hasattr(resp_data, 'messages'): raw_resp_msgs = resp_data.messages
          elif isinstance(resp_data, dict) and 'messages' in resp_data: raw_resp_msgs = resp_data.get('messages', [])
          elif isinstance(resp_data, list): raw_resp_msgs = resp_data
          processed_resp_msgs = []
          for m in raw_resp_msgs:
              if hasattr(m, 'model_dump'): processed_resp_msgs.append(m.model_dump(exclude_none=True))
              elif isinstance(m, dict): processed_resp_msgs.append(m.copy())
              else: processed_resp_msgs.append(m)
          current_history.extend(processed_resp_msgs)
     mock_history_container['history'] = current_history

@pytest.mark.django_db(transaction=True)
class TestChat(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='password')
        cls.chat_url = reverse('chat_completions')

    def setUp(self):
        self.client.login(username='testuser', password='password')
        self.patcher = patch('swarm.views.utils.get_blueprint_instance')
        self.mock_get_blueprint = self.patcher.start()
        self.dummy_blueprint_instance = DummyBlueprint(config={})
        self.mock_get_blueprint.return_value = self.dummy_blueprint_instance
        global mock_history_container; mock_history_container = {'history': []}

    def tearDown(self): self.patcher.stop()

    def test_authentication_required(self):
        with patch('swarm.views.utils.store_conversation_history') as mock_store_hist, \
             patch('swarm.views.utils.serialize_swarm_response', return_value={'choices':[{'message':{'role':'assistant','content':'Mocked serialized'}}]}) as mock_serialize:
            self.client.logout()
            payload = { "model": "dummy_blueprint", "messages": [{"role": "user", "content": "Hello"}] }
            response = self.client.post(self.chat_url, data=json.dumps(payload), content_type="application/json")
            if os.getenv("ENABLE_API_AUTH", "False").lower() == "true":
                 self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            else:
                 # Auth disabled, view calls asyncio.run(), patches should allow 200
                 self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_payload(self):
        payload = { "model": "dummy_blueprint" }
        response = self.client.post(self.chat_url, data=json.dumps(payload), content_type="application/json", HTTP_AUTHORIZATION='Bearer dummy-token')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("'messages' field is required", response.json().get('error', ''))

    def test_blueprint_not_found(self):
        self.mock_get_blueprint.side_effect = FileNotFoundError("Blueprint not found")
        payload = { "model": "nonexistent_blueprint", "messages": [{"role": "user", "content": "Hello"}] }
        response = self.client.post(self.chat_url, data=json.dumps(payload), content_type="application/json", HTTP_AUTHORIZATION='Bearer dummy-token')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Blueprint not found", response.json().get("error", ""))

    def test_stateless_chat(self):
        with patch('swarm.views.utils.store_conversation_history') as mock_store_hist, \
             patch('swarm.views.utils.serialize_swarm_response', return_value={'id': 'mock-id', 'choices': [{'message': {'role': 'assistant', 'content': 'Mocked response'}}], 'usage': {'total_tokens': 10}}) as mock_serialize:
            payload = { "model": "dummy_blueprint", "messages": [{"role": "user", "content": "Hello"}] }
            response = self.client.post(self.chat_url, data=json.dumps(payload), content_type="application/json", HTTP_AUTHORIZATION='Bearer dummy-token')
            if response.status_code != 200: print("ERROR Response Content:", response.content.decode())
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # run_conversation calls blueprint.run_with_context_async
            # Check the mock on the *instance* created in setUp
            self.dummy_blueprint_instance.run_with_context_async.assert_called_once()
            response_data = response.json(); self.assertIn('choices', response_data); self.assertGreater(len(response_data['choices']), 0)
            self.assertEqual(response_data['choices'][0]['message']['role'], 'assistant')
            self.assertEqual(response_data['choices'][0]['message']['content'], 'Mocked response')
            mock_store_hist.assert_called_once(); mock_serialize.assert_called_once()

    # Test is synchronous
    def test_stateful_chat(self):
        """Test stateful chat - PATCHING run_conversation to bypass async issues."""
        conversation_id = f"test-conv-{uuid.uuid4()}"
        global mock_history_container
        # Define SYNC mock response for the patched run_conversation
        mock_run_conv_response_sync = (
             Response(messages=[ChatMessage(role="assistant", content="Mocked response from run_conv")]),
             {"active_agent_name": "DummyAgent", "turn": 1}
        )
        # Patch load, store, serialize, AND run_conversation
        with patch('swarm.views.utils.load_conversation_history', lambda conv_id, current_msgs, tool_id=None: [m.copy() for m in mock_history_container['history']] + current_msgs), \
             patch('swarm.views.utils.store_conversation_history', mock_store), \
             patch('swarm.views.utils.serialize_swarm_response', return_value={'id': 'mock-id', 'choices': [{'message': {'role': 'assistant', 'content': 'Mocked response'}}], 'usage': {'total_tokens': 10}}) as mock_serialize, \
             patch('swarm.views.utils.run_conversation', return_value=mock_run_conv_response_sync) as mock_run_conv: # Patch run_conversation as sync

            # --- Turn 1 ---
            payload_1 = { "model": "dummy_blueprint", "messages": [{"role": "user", "content": "First message"}], "metadata": {"conversationId": conversation_id} }
            response_1 = self.client.post( self.chat_url, data=json.dumps(payload_1), content_type="application/json", HTTP_AUTHORIZATION='Bearer dummy-token')
            self.assertEqual(response_1.status_code, status.HTTP_200_OK)
            mock_run_conv.assert_called_once() # Check the patched sync function
            call_args_1, _ = mock_run_conv.call_args
            messages_passed_1 = call_args_1[1] # blueprint_instance, messages_extended, context_vars
            self.assertEqual(len(messages_passed_1), 1); self.assertEqual(messages_passed_1[0]["content"], "First message")
            self.assertEqual(len(mock_history_container['history']), 2)
            self.assertEqual(mock_history_container['history'][1]["content"], "Mocked response from run_conv") # Comes from mock_run_conv_response

            mock_run_conv.reset_mock(); mock_serialize.reset_mock()

            # --- Turn 2 ---
            payload_2 = { "model": "dummy_blueprint", "messages": [{"role": "user", "content": "Second message"}], "metadata": {"conversationId": conversation_id} }
            response_2 = self.client.post( self.chat_url, data=json.dumps(payload_2), content_type="application/json", HTTP_AUTHORIZATION='Bearer dummy-token')
            self.assertEqual(response_2.status_code, status.HTTP_200_OK)
            mock_run_conv.assert_called_once()
            call_args_2, _ = mock_run_conv.call_args
            messages_passed_2 = call_args_2[1]
            self.assertEqual(len(messages_passed_2), 3) # History + new
            self.assertEqual(messages_passed_2[0]["content"], "First message")
            self.assertEqual(messages_passed_2[1]["content"], "Mocked response from run_conv")
            self.assertEqual(messages_passed_2[2]["content"], "Second message")
            self.assertEqual(len(mock_history_container['history']), 4)
            self.assertEqual(mock_history_container['history'][3]["content"], "Mocked response from run_conv")
            mock_serialize.assert_called_once()

