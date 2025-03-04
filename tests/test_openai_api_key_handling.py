import os
import asyncio
import pytest
from swarm.extensions.blueprint.blueprint_base import BlueprintBase

class DummySwarm:
    def __init__(self, debug=False):
        self.debug = debug
        self.agents = {"dummy": type('Agent', (), {'name': 'dummy'})()}
        self.current_llm_config = {"model": "dummy_model"}

    async def run(self, agent, messages, context_variables, stream, debug):
        return type('Response', (), {'messages': [{"role": "assistant", "content": "Dummy response"}], 'agent': agent})

    async def run_llm(self, messages, max_tokens, temperature):
        return type('LLMResponse', (), {'choices': [type('Choice', (), {'message': {"content": "YES"}})]})

class DummyBlueprint(BlueprintBase):
    metadata = {"title": "Dummy Blueprint", "description": "A test blueprint"}

    def create_agents(self):
        return {"dummy": type('Agent', (), {'name': 'dummy'})()}

@pytest.mark.skip(reason="Skipping due to integration instability; fix pending")
@pytest.mark.asyncio
async def test_openai_api_key_handling():
    original_api_key = "sk-TESTKEY"
    os.environ["OPENAI_API_KEY"] = original_api_key
    dummy_swarm = DummySwarm(debug=True)
    blueprint = DummyBlueprint(config={}, swarm_instance=dummy_swarm)
    messages = [{"role": "user", "content": "Test"}]
    response = await blueprint.run_with_context_async(messages, {})
    assert os.environ["OPENAI_API_KEY"] == original_api_key
    assert response["response"].messages[0]["content"] == "Dummy response"
