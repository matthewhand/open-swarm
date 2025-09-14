import json
import os
import sqlite3
from unittest.mock import MagicMock

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
def poets_blueprint_instance(tmp_path):
    db_path_str = str(tmp_path / "test_swarm_instructions.db")
    config_file_str = str(tmp_path / "test_swarm_config.json")

    with open(config_file_str, 'w') as f:
        json.dump(MINIMAL_CONFIG_CONTENT, f)

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
    assert agent.instructions and agent.instructions.strip().startswith("You are"), \
        f"Agent instructions for '{agent.name}' seem invalid or empty: '{agent.instructions}'"


@pytest.mark.skip(reason="Blueprint interaction tests not yet implemented")
def test_poets_collaboration_flow(poets_blueprint_instance):
    pass

@pytest.mark.skip(reason="Blueprint CLI tests not yet implemented")
def test_poets_cli_execution():
    pass
