import json
import os
import sqlite3
from unittest.mock import MagicMock, AsyncMock

import pytest
from agents import Agent as GenericAgent
from swarm.blueprints.poets.blueprint_poets import PoetsBlueprint

# A minimal valid config that includes a 'default' LLM profile
MINIMAL_CONFIG_CONTENT = {
    "llm": {
        "default": {
            "model": "gpt-mock",
            "provider": "openai",
            "api_key": "test_key",
            "base_url": "http://localhost:1234"
        }
    },
    "blueprints": {
        "poets-society": {
            "starting_poet": "Gritty Buk",
            "model_profile": "default"
        }
    }
}

@pytest.fixture
def poets_blueprint_instance(tmp_path, monkeypatch):
    db_path_str = str(tmp_path / "test_swarm_instructions.db")
    config_file_str = str(tmp_path / "test_swarm_config.json")

    with open(config_file_str, 'w') as f:
        json.dump(MINIMAL_CONFIG_CONTENT, f)

    # Patch the _load_configuration method in BlueprintBase to use the minimal config
    def mock_load_configuration(self):
        self._config = MINIMAL_CONFIG_CONTENT
        import os
        def redact(val):
            if not isinstance(val, str) or len(val) <= 4:
                return "****"
            return val[:2] + "*" * (len(val)-4) + val[-2:]
        def redact_dict(d):
            if isinstance(d, dict):
                return {k: (redact_dict(v) if not (isinstance(v, str) and ("key" in k.lower() or "token" in k.lower() or "secret" in k.lower())) else redact(v)) for k, v in d.items()}
            elif isinstance(d, list):
                return [redact_dict(item) for item in d]
            return d
        from swarm.core.blueprint_base import logger
        logger.debug(f"Loaded config (redacted): {redact_dict(self._config)}")

    monkeypatch.setattr('swarm.core.blueprint_base.BlueprintBase._load_configuration', mock_load_configuration)

    bp = PoetsBlueprint(
        blueprint_id="poets-society",
        config_path=config_file_str,
        db_path_override=db_path_str
    )
    yield bp

    if os.path.exists(db_path_str):
        os.remove(db_path_str)
    if os.path.exists(config_file_str):
        os.remove(config_file_str)

def test_poets_db_initialization(poets_blueprint_instance):
    blueprint = poets_blueprint_instance
    # print(f"DEBUG: Attributes of blueprint instance: {dir(blueprint)}", file=sys.stderr) # DEBUG
    assert hasattr(blueprint, 'db_path'), "PoetsBlueprint instance should have a db_path attribute"
    assert isinstance(blueprint.db_path, str), "Blueprint's db_path is not a string"
    assert os.path.exists(blueprint.db_path), f"Test DB not found at {blueprint.db_path}"

    conn = sqlite3.connect(blueprint.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM agent_instructions WHERE agent_name LIKE '%Poe%'")
    count = cursor.fetchone()[0]
    conn.close()
    assert count > 0, "Default poet instructions not loaded into DB"

def test_poets_agent_creation(poets_blueprint_instance):
    blueprint = poets_blueprint_instance
    assert blueprint.config is not None, "Blueprint config not loaded"
    default_profile = blueprint.get_llm_profile("default")
    assert default_profile is not None, "LLM profile 'default' missing in config"
    assert default_profile.get("model") == "gpt-mock", "LLM profile 'default' model mismatch"

    m1 = MagicMock(); m1.name = "memory"
    m2 = MagicMock(); m2.name = "filesystem"
    m3 = MagicMock(); m3.name = "mcp-shell"
    mock_mcp_list = [m1, m2, m3]

    starting_agent_name_from_config = MINIMAL_CONFIG_CONTENT["blueprints"]["poets-society"]["starting_poet"]
    # The blueprint's __init__ sets self.starting_agent_name from self.poet_config
    # self.poet_config is self.config.get("blueprints", {}).get(self.NAME, {})
    # And self.NAME is "poets-society"
    assert hasattr(blueprint, 'starting_agent_name'), "Blueprint missing 'starting_agent_name'"
    assert blueprint.starting_agent_name == starting_agent_name_from_config

    agent = blueprint.create_starting_agent(mcp_servers=mock_mcp_list)
    assert agent is not None
    assert isinstance(agent, GenericAgent)
    assert agent.name == starting_agent_name_from_config

    valid_poets = [
        "Raven Poe", "Mystic Blake", "Bard Whit", "Echo Plath",
        "Frosted Woods", "Harlem Lang", "Verse Neru", "Haiku Bash",
        "Gritty Buk"
    ]
    assert agent.name in valid_poets, f"Agent name '{agent.name}' not in valid poets list."

    assert agent.model is not None, "Agent should have a model configured."
    assert len(agent.tools) > 0, "Poet agent should have other poets as tools."
    # Check that instructions attribute exists and is a string that starts with "You are"
    assert hasattr(agent, 'instructions'), "Agent should have instructions attribute"
    assert agent.instructions is not None, "Agent instructions should not be None"
    assert isinstance(agent.instructions, str), "Agent instructions should be a string"
    assert agent.instructions.strip().startswith("You are"), \
        f"Agent instructions for '{agent.name}' seem invalid or empty: '{agent.instructions}'"


@pytest.mark.asyncio
async def test_poets_collaboration_flow(poets_blueprint_instance, mocker):
    """Test collaboration flow: starting poet delegates to another poet via tool call."""
    blueprint = poets_blueprint_instance

    # Create mock MCP server
    mock_mcp = MagicMock(name="mock_mcp")

    # Get agents and tools
    agents, tools = blueprint.create_agents_and_tools([mock_mcp])
    starting_agent_name = blueprint.starting_agent_name
    starting_agent = agents[starting_agent_name]

    # Select another poet for delegation
    other_poet_name = "Raven Poe"
    assert other_poet_name in agents, f"{other_poet_name} not in agents"
    other_agent = agents[other_poet_name]

    # Verify starting agent has the other poet as a tool
    assert any(tool.name == other_poet_name for tool in starting_agent.tools)

    # Mock Runner.run_streamed for the starting agent
    mock_starting_result = MagicMock()

    async def mock_starting_stream_events():
        events = [
            {
                "type": "step",
                "output": {
                    "messages": [{
                        "role": "assistant",
                        "content": "I'll delegate to another poet.",
                        "tool_calls": [{
                            "id": "call_123",
                            "function": {
                                "name": other_poet_name,
                                "arguments": json.dumps({
                                    "messages": [{"role": "user", "content": "Write a gothic poem about lost love."}]
                                })
                            }
                        }]
                    }]
                }
            },
            {
                "type": "step",
                "output": {
                    "messages": [{
                        "role": "tool",
                        "content": "In shadowed halls where memories decay,\nLost love's lament in raven's cry does play...\nEternal night claims what the heart once knew,\nIn gothic verse, our sorrow ever true.",
                        "tool_call_id": "call_123"
                    }]
                }
            }
        ]
        for event in events:
            yield event

    mock_starting_result.stream_events = mock_starting_stream_events

    # Mock Runner.run_streamed for the other agent
    mock_other_result = MagicMock()

    async def mock_other_stream_events():
        events = [
            {
                "type": "step",
                "output": {
                    "messages": [{
                        "role": "assistant",
                        "content": "In shadowed halls where memories decay,\nLost love's lament in raven's cry does play...\nEternal night claims what the heart once knew,\nIn gothic verse, our sorrow ever true."
                    }]
                }
            }
        ]
        for event in events:
            yield event

    mock_other_result.stream_events = mock_other_stream_events

    # Patch Runner.run_streamed to return our mocks
    def mock_run_streamed_side_effect(starting_agent, input, **kwargs):
        if starting_agent.name == other_poet_name:
            return mock_other_result
        else:
            return mock_starting_result

    mocker.patch('agents.run.Runner.run_streamed', side_effect=mock_run_streamed_side_effect)

    # Run the blueprint and collect responses
    user_messages = [{"role": "user", "content": "Write a gothic poem about lost love."}]
    collected_content = []
    async for chunk in blueprint.run(user_messages, mcp_servers=[mock_mcp]):
        if "messages" in chunk and len(chunk["messages"]) > 0:
            message = chunk["messages"][0]
            if "content" in message:
                collected_content.append(message["content"])

    # Assert final content is the poem from the delegated agent
    final_poem = "".join(collected_content)
    assert "gothic" in final_poem.lower()
    assert "lost love" in final_poem.lower()
    assert len(final_poem) > 50  # Basic length check

@pytest.mark.skip(reason="Blueprint CLI tests not yet implemented")
def test_poets_cli_execution():
    pass
