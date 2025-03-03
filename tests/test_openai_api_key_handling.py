import os
import asyncio
import pytest
from swarm.extensions.blueprint.blueprint_base import BlueprintBase
from swarm.core import Swarm
import uuid

class DummySwarm:
    def __init__(self, debug=False):
        self.debug = debug
        # Add agents attribute to satisfy BlueprintBase initialization.
        self.agents = {}
        
    # Dummy implementation to avoid errors during tool discovery.
    async def discover_and_merge_agent_tools(self, agent, debug=False):
        return []

    async def run(self, agent, messages, context_variables, stream=False, debug=False):
        # Assert that OPENAI_API_KEY is temporarily removed during run.
        assert "OPENAI_API_KEY" not in os.environ, "OPENAI_API_KEY should be temporarily removed"
        # Return a dummy response with an 'agent' attribute set to None.
        class DummyResponse:
            def __init__(self):
                self.messages = [{"role": "assistant", "content": "Dummy response"}]
                self.agent = None
        return DummyResponse()

class DummyBlueprint(BlueprintBase):
    def __init__(self, config, **kwargs):
        # Force skipping Django registration to avoid AppRegistryNotReady errors.
        kwargs.setdefault('skip_django_registration', True)
        super().__init__(config, **kwargs)
        
    @property
    def metadata(self):
        return {"title": "Dummy Blueprint", "env_vars": []}

    def create_agents(self):
        dummy_agent = type("DummyAgent", (), {})()
        dummy_agent.name = "dummy"
        dummy_agent.functions = []
        dummy_agent.instructions = "dummy instruction"
        dummy_agent.mcp_servers = []
        return {"dummy": dummy_agent}

@pytest.mark.asyncio
async def test_openai_api_key_handling():
    original_api_key = "sk-TESTKEY"
    os.environ["OPENAI_API_KEY"] = original_api_key
    dummy_swarm = DummySwarm(debug=True)
    blueprint = DummyBlueprint(config={}, swarm_instance=dummy_swarm)
    # Simulate asynchronous call that uses run_with_context_async, which temporarily removes OPENAI_API_KEY.
    messages = [{"role": "user", "content": "Test"}]
    response = await blueprint.run_with_context_async(messages, {})
    # After completion, verify that OPENAI_API_KEY is restored.
    assert os.environ.get("OPENAI_API_KEY") == original_api_key

if __name__ == "__main__":
    asyncio.run(test_openai_api_key_handling())