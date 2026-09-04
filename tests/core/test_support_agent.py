from swarm.core.support_agent import SUPPORT_AGENT_ID, support_agent_spec


def test_support_spec_has_role_and_blueprint_brief():
    spec = support_agent_spec()
    assert spec["agent_id"] == SUPPORT_AGENT_ID
    assert spec["role"] == "support"
    assert spec["agent_type"] == "api"
    assert "BlueprintBase" in spec["instructions"]
    assert "first agent team" in spec["instructions"]
