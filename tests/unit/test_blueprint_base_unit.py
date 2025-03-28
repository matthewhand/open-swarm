"""Unit tests for BlueprintBase functionality.
These tests verify basic behavior for setting and retrieving agents,
context variable updates, and truncating message history.
"""

import pytest  # type: ignore

import asyncio
from typing import Any
from swarm.extensions.blueprint.blueprint_base import BlueprintBase, ChatMessage, Response
from swarm.extensions.blueprint.agent_utils import get_agent_name
from agents.agent import Agent
from agents.tool import Tool

# Define a DummyTool to satisfy the Agent.as_tool return type.
# Since "Tool" is not a concrete class, we omit inheritance and create a dummy class.
class DummyTool:
    def __init__(self, name: str, description: str, custom_output_extractor: Any = None) -> None:
        self.name = name
        self.description = description
        self.custom_output_extractor = custom_output_extractor

# DummyAgent now subclasses Agent for type compatibility.
class DummyAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name
        self.handoffs = []  # Simulate agent having handoffs

    # Adjusted signature to match the base class.
    def as_tool(self, tool_name: str | None = None, tool_description: str | None = None, custom_output_extractor: Any = None) -> Tool:
        # Return a DummyTool instance; cast it to Tool if necessary.
        return DummyTool(tool_name or "", tool_description or "", custom_output_extractor)  # type: ignore

# Dummy blueprint derived from BlueprintBase for unit testing.
class DummyBlueprint(BlueprintBase):
    @property
    def metadata(self) -> dict:
        return {
            "title": "DummyBlueprint",
            "env_vars": [],
            "required_mcp_servers": [],
            "max_context_tokens": 1000,
            "max_context_messages": 10
        }

    def create_agents(self) -> dict[str, Agent]:
        # Create a dummy agent named "dummy"
        return {"dummy": DummyAgent("dummy")}

def test_set_and_get_starting_agent():
    bp = DummyBlueprint(config={})
    agents = bp.create_agents()
    bp.agents = agents
    bp.set_starting_agent(agents["dummy"])
    assert bp.starting_agent == agents["dummy"]
    # Assuming get_agent_name returns the agent's name string.
    assert bp.context_variables.get("active_agent_name") == "dummy"

@pytest.mark.asyncio
async def test_determine_active_agent_with_starting():
    bp = DummyBlueprint(config={})
    agents = bp.create_agents()
    bp.agents = agents
    bp.set_starting_agent(agents["dummy"])
    active = await bp.determine_active_agent()
    assert active == agents["dummy"]

def test_truncate_message_history():
    bp = DummyBlueprint(config={})
    # Create 15 dummy messages, each a dict with role and content.
    messages = [{"role": "user", "content": f"msg{i}"} for i in range(15)]
    truncated = bp.truncate_message_history(messages, "dummy-model")
    # Expect the truncated list to be at most the max_context_messages (10).
    assert len(truncated) <= 10

# Test _is_create_agents_overridden functionality.
def test_is_create_agents_overridden():
    bp = DummyBlueprint(config={})
    # For DummyBlueprint, create_agents is overridden, so _is_create_agents_overridden should return True.
    assert bp._is_create_agents_overridden() is True

# Test run_with_context behavior with no valid input message.
def test_run_with_context_empty_input():
    bp = DummyBlueprint(config={})
    bp.agents = {"dummy": DummyAgent("dummy")}
    bp.set_starting_agent(bp.agents["dummy"])
    # Provide an empty messages list.
    result = bp.run_with_context([], {"user_goal": ""})
    # For our test, we simply check that context_variables remain a dict.
    assert isinstance(result.get("context_variables"), dict)

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main())
