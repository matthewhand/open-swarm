from unittest.mock import MagicMock

from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint
from swarm.core.agent_config import AgentConfig


def test_get_agent_config_maps_mcp_assignments():
    """Ensure _get_agent_config respects agent_mcp_assignments and returns AgentConfig."""
    # Provide minimal inline config to avoid file IO
    cfg = {
        "agents": {
            "Coordinator": {
                "instructions": "Coordinate the geese.",
                "model_profile": "default",
                "tools": []
            }
        },
        "llm": {"default": {"provider": "mock", "model": "mock-model"}},
        "settings": {"default_llm_profile": "default"},
    }

    bp = GeeseBlueprint(blueprint_id="test_geese_mcp_cfg", agent_mcp_assignments={"Coordinator": ["filesystem", "memory"]})
    # Directly inject config dict to sidestep loader
    bp._config = cfg

    agent_cfg = bp._get_agent_config("Coordinator")
    assert isinstance(agent_cfg, AgentConfig)
    assert [s.name for s in agent_cfg.mcp_servers] == ["filesystem", "memory"]


def test_create_agent_from_config_handles_sdk_presence_or_absence():
    """create_agent_from_config returns a usable agent object both with and without the SDK present."""
    cfg = AgentConfig(
        name="Coordinator",
        instructions="Coordinate the geese.",
        tools=[],
        model_profile="default",
        mcp_servers=[],
    )
    bp = GeeseBlueprint(blueprint_id="test_geese_create_agent")

    agent = bp.create_agent_from_config(cfg)
    # If SDK missing, a MagicMock is returned; otherwise an SDK Agent instance.
    if isinstance(agent, MagicMock):
        assert hasattr(agent, "model")
        # Basic attribute mirroring
        assert agent.name == "Coordinator"
        assert agent.instructions == "Coordinate the geese."
    else:
        # Avoid invoking networked run(); just validate core attributes
        assert getattr(agent, "name", None) == "Coordinator"
        assert getattr(agent, "instructions", None) == "Coordinate the geese."
        # mcp_servers should exist (may be empty)
        assert isinstance(getattr(agent, "mcp_servers", []), list)
