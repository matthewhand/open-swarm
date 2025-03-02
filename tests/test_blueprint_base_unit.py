import pytest
from swarm.extensions.blueprint.blueprint_base import BlueprintBase

class DummyAgent:
    def __init__(self, name):
        self.name = name

class FakeBlueprint(BlueprintBase):
    @property
    def metadata(self):
        return {"title": "Fake Blueprint", "description": "Test blueprint"}

@pytest.mark.asyncio
async def test_run_with_context():
    dummy_agent = DummyAgent("agent1")
    blueprint = FakeBlueprint(config={"llm": {"default": {"dummy": "dummy"}}})
    blueprint.set_starting_agent(dummy_agent)

    class FakeResponse:
        def __init__(self, messages, agent):
            self.messages = messages
            self.agent = agent

    class FakeSwarm:
        def __init__(self, agent):
            self.agents = {agent.name: agent}
        async def run(self, agent, messages, context_variables, stream, debug):
            return FakeResponse(messages + [{"role": "assistant", "content": "Test Completed", "sender": agent.name}], agent)

    blueprint.swarm = FakeSwarm(dummy_agent)
    messages = [{"role": "user", "content": "Hello"}]
    context = {"foo": "bar"}
    result = await blueprint.run_with_context(messages, context)
    assert "Test Completed" in result["response"].messages[-1]["content"]
