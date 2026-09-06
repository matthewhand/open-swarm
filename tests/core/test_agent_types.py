from swarm.core.agent_types import (
    AGENT_TYPES,
    agent_type_for_kind,
    public_personas,
)


def test_kind_maps_to_api_cli_or_remote():
    assert AGENT_TYPES == ("api", "cli", "remote")
    assert agent_type_for_kind("builtin") == "api"
    assert agent_type_for_kind("personality") == "api"
    assert agent_type_for_kind("swarm") == "api"
    assert agent_type_for_kind("blueprint") == "api"
    assert agent_type_for_kind("api") == "api"
    assert agent_type_for_kind("cli") == "cli"
    assert agent_type_for_kind("remote") == "remote"
    assert agent_type_for_kind("herdr") == "remote"
    assert agent_type_for_kind("hermes") == "remote"
    assert agent_type_for_kind("omb") == "remote"
    assert agent_type_for_kind(None) == "api"
    assert "herdr" not in AGENT_TYPES


def test_public_personas_drops_nameless():
    assert public_personas([
        {"name": "A", "instructions": "alpha"},
        {"name": "  ", "instructions": "skip"},
        "nope",
    ]) == [{"name": "A", "instructions": "alpha"}]
