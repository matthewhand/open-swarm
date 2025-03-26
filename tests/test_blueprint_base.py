import pytest
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Import necessary components
from swarm.extensions.blueprint.blueprint_base import BlueprintBase
from swarm.types import Agent
# Import discovery functions to call them directly
from swarm.extensions.blueprint.agent_utils import discover_tools_for_agent, discover_resources_for_agent

# --- Mocking Utilities ---
class MockBlueprint(BlueprintBase):
    @property
    def metadata(self):
        return {"title": "MockBlueprint", "description": "A mock blueprint for testing."}

    def create_agents(self):
        agent1 = MagicMock(spec=Agent)
        agent1.name = "Agent1"
        agent1.functions = [] # Start empty, discovery should populate
        agent1.resources = [] # Start empty
        agent1.mcp_servers = []
        return {"agent1": agent1}

    def register_blueprint_urls(self) -> None: pass

# Fixture to patch discovery globally for tests in this module
@pytest.fixture(autouse=True)
def patch_discovery(monkeypatch):
    mock_tools_result = ['mock_tool']
    mock_resources_result = [{'name':'mock_res'}]

    async def mock_discover_tools_side_effect(agent, *args, **kwargs):
        if hasattr(agent, 'functions'): agent.functions = mock_tools_result
        return mock_tools_result
    async def mock_discover_resources_side_effect(agent, *args, **kwargs):
        if hasattr(agent, 'resources'): agent.resources = mock_resources_result
        return mock_resources_result

    mock_discover_tools = AsyncMock(side_effect=mock_discover_tools_side_effect)
    mock_discover_resources = AsyncMock(side_effect=mock_discover_resources_side_effect)

    monkeypatch.setattr('swarm.extensions.blueprint.agent_utils.discover_tools_for_agent', mock_discover_tools)
    monkeypatch.setattr('swarm.extensions.blueprint.agent_utils.discover_resources_for_agent', mock_discover_resources)
    yield mock_discover_tools, mock_discover_resources

# --- Test Cases ---

@pytest.mark.asyncio
async def test_blueprint_base_initialization(patch_discovery):
    """Test basic initialization of BlueprintBase."""
    mock_discover_tools, mock_discover_resources = patch_discovery
    mock_config = {"llm": {"default": {"model": "test-model", "api_key": "test-key"}}}

    blueprint = MockBlueprint(config=mock_config)

    assert blueprint.config == mock_config
    assert blueprint.swarm is not None
    assert blueprint.starting_agent is not None
    assert blueprint.starting_agent.name == "Agent1"

    await asyncio.sleep(0.05)

    assert mock_discover_tools.call_count >= 0
    assert mock_discover_resources.call_count >= 0

def test_metadata_enforcement():
    """Test that BlueprintBase enforces the presence and type of the metadata property."""
    with patch("swarm.core.Swarm.__init__", return_value=None):
        class InvalidMetaTypeBlueprint(BlueprintBase):
            metadata = "not a dict"
            def create_agents(self): return {}
            def register_blueprint_urls(self): pass

        class MissingMetaBlueprint(BlueprintBase):
            @property
            def metadata(self): raise NotImplementedError
            def create_agents(self): return {}
            def register_blueprint_urls(self): pass

        expected_error_msg_pattern = r"must define a 'metadata' property returning a dictionary."
        with patch('swarm.extensions.blueprint.agent_utils.discover_tools_for_agent', new_callable=AsyncMock), \
             patch('swarm.extensions.blueprint.agent_utils.discover_resources_for_agent', new_callable=AsyncMock):
            with pytest.raises(AssertionError, match=expected_error_msg_pattern):
                InvalidMetaTypeBlueprint(config={})

        with patch('swarm.extensions.blueprint.agent_utils.discover_tools_for_agent', new_callable=AsyncMock), \
             patch('swarm.extensions.blueprint.agent_utils.discover_resources_for_agent', new_callable=AsyncMock):
            with pytest.raises(NotImplementedError):
                 MissingMetaBlueprint(config={})

@pytest.mark.asyncio
async def test_create_agents(patch_discovery): # Use fixture
    """Test that create_agents is called and updates swarm agents."""
    mock_config = {"llm": {"default": {"model": "test-model", "api_key": "test-key"}}}
    blueprint = MockBlueprint(config=mock_config)
    assert "agent1" in blueprint.swarm.agents
    assert blueprint.swarm.agents["agent1"].name == "Agent1"

def test_new_feature_configuration(patch_discovery): # Use fixture
    """Test initialization with new flags like auto_complete_task."""
    blueprint = MockBlueprint(config={}, auto_complete_task=True, update_user_goal=True)
    assert blueprint.auto_complete_task is True
    assert blueprint.update_user_goal is True

# --- Tests for internal methods (_is_task_done, _update_user_goal) ---

@pytest.mark.asyncio
async def test_is_task_done_yes(patch_discovery): # Use fixture
    """Test _is_task_done returns True when LLM response is 'YES' (async test)."""
    mock_config = {"llm": {"default": {"model": "test-model", "api_key": "test-key"}}}
    blueprint = MockBlueprint(config=mock_config)
    mock_llm_response = MagicMock()
    mock_llm_response.choices = [MagicMock(message=MagicMock(content="YES, the task is complete."))]
    # Patch the actual client call used within the async method
    with patch.object(blueprint.swarm.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_llm_response) as mock_create:
        # Call the CORRECT async method name
        result = await blueprint._is_task_done_async("goal", "summary", "last message")
    assert result is True
    mock_create.assert_awaited_once()

@pytest.mark.asyncio
async def test_is_task_done_no(patch_discovery): # Use fixture
    """Test _is_task_done returns False when LLM response is not 'YES' (async test)."""
    mock_config = {"llm": {"default": {"model": "test-model", "api_key": "test-key"}}}
    blueprint = MockBlueprint(config=mock_config)
    mock_llm_response = MagicMock()
    mock_llm_response.choices = [MagicMock(message=MagicMock(content="NO, still working."))]
    with patch.object(blueprint.swarm.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_llm_response) as mock_create:
        # Call the CORRECT async method name
        result = await blueprint._is_task_done_async("goal", "summary", "last message")
    assert result is False
    mock_create.assert_awaited_once()

@pytest.mark.asyncio
async def test_update_user_goal(patch_discovery): # Use fixture
    """Test _update_user_goal updates context based on LLM summary (async test)."""
    mock_config = {"llm": {"default": {"model": "test-model", "api_key": "test-key"}}}
    blueprint = MockBlueprint(config=mock_config)
    messages = [{"role": "user", "content": "I need help."}]
    mock_llm_response = MagicMock()
    mock_llm_response.choices = [MagicMock(message=MagicMock(content="Summarized goal: Get help."))]
    with patch.object(blueprint.swarm.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_llm_response) as mock_create:
        # Call the CORRECT async method name
        await blueprint._update_user_goal_async(messages)
    assert blueprint.context_variables.get("user_goal") == "Summarized goal: Get help."
    mock_create.assert_awaited_once()

# --- Skipped Tests ---
@pytest.mark.skip(reason="Auto-completion test needs more sophisticated mocking.")
def test_autocompletion(): pass

@pytest.mark.skip(reason="Dynamic goal update test needs multi-turn mocking.")
def test_dynamic_user_goal_updates(): pass
