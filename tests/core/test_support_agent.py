from swarm.core.support_agent import SUPPORT_AGENT_ID, support_agent_spec


def test_support_spec_has_role_and_blueprint_brief():
    spec = support_agent_spec()
    assert spec["agent_id"] == SUPPORT_AGENT_ID
    assert spec["role"] == "support"
    assert spec["agent_type"] == "api"
    assert "BlueprintBase" in spec["instructions"]
    assert "ApiKindBase" in spec["instructions"]
    assert "CliKindBase" in spec["instructions"]
    assert "RemoteKindBase" in spec["instructions"]
    assert "Create a team" in spec["instructions"]
    assert "SUPPORT_NL_BLUEPRINT_NO_USER_PYTHON" in spec["instructions"]
    assert "do not write Python" in spec["instructions"].lower() or "do not dump" in spec["instructions"].lower()
    assert "ONBOARD_JOURNEY_CLI_API_REMOTE" in spec["instructions"]
    assert "Add a remote" in spec["instructions"]
    assert "Wire a CLI" in spec["instructions"]
    assert "Hermes" in spec["instructions"]
    assert "OpenMousBot" in spec["instructions"]
    assert "Herdr" in spec["instructions"]
    assert "one-pane" in spec["instructions"] or "one pane" in spec["instructions"]
    assert ":8001" not in spec["instructions"]
