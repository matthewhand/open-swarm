"""First-class agent roles: normalize, roster, API payload, AgentConfig."""

from swarm.core.agent_config import AgentConfig
from swarm.core.agent_roles import (
    CANONICAL_ROLES,
    ROLE_CSS_CLASSES,
    ROLE_DEFAULT,
    ROLE_GATE,
    ROLE_SKEPTIC,
    ROLE_SUPPORT,
    attach_role,
    blueprint_role_fields,
    find_role_agent,
    find_role_name,
    normalize_agent_role,
    normalize_roster,
    role_css_class,
    role_from_agent,
)


def test_normalize_aliases_and_unknown_specializations():
    assert normalize_agent_role("tool_gate") == ROLE_GATE
    assert normalize_agent_role("tool-gate") == ROLE_GATE
    assert normalize_agent_role("GATE") == ROLE_GATE
    assert normalize_agent_role("reviewer") == ROLE_SKEPTIC
    assert normalize_agent_role("support") == ROLE_SUPPORT
    assert normalize_agent_role("Writer") == ROLE_DEFAULT
    assert normalize_agent_role(None) == ROLE_DEFAULT
    assert normalize_agent_role("") == ROLE_DEFAULT


def test_css_class_names_are_stable_for_support_ui():
    assert ROLE_CSS_CLASSES == {
        "default": "os-agent-role-default",
        "support": "os-agent-role-support",
        "gate": "os-agent-role-gate",
        "skeptic": "os-agent-role-skeptic",
    }
    for role in CANONICAL_ROLES:
        assert role_css_class(role) == f"os-agent-role-{role}"
    assert role_css_class("tool_gate") == "os-agent-role-gate"


def test_agent_config_role_is_first_class_and_normalized():
    cfg = AgentConfig(name="Gate", instructions="classify", role="tool_gate")
    assert cfg.role == ROLE_GATE
    default = AgentConfig(name="Worker", instructions="do work")
    assert default.role == ROLE_DEFAULT


def test_find_role_agent_unwired_is_none():
    roster = [
        {"name": "Writer", "role": "default"},
        {"name": "Researcher", "role": "default"},
    ]
    assert find_role_agent(roster, "gate") is None
    assert find_role_name(roster, "skeptic") is None


def test_find_role_agent_and_roster():
    gate = attach_role(type("A", (), {"name": "ToolGate"})(), "tool_gate")
    agents = {
        "Writer": {"name": "Writer", "role": "default"},
        "ToolGate": gate,
    }
    assert find_role_agent(agents, "gate") is gate
    assert find_role_name(agents, "gate") == "ToolGate"
    assert role_from_agent(gate) == ROLE_GATE
    roster = normalize_roster(agents)
    assert {"name": "Writer", "role": "default"} in roster
    assert {"name": "ToolGate", "role": "gate"} in roster


def test_blueprint_role_fields_default_when_unwired():
    fields = blueprint_role_fields({
        "name": "Alpha",
        "agents": ["bot_a", "bot_b"],
    })
    assert fields["role"] == "default"
    assert fields["gate_agent"] is None
    assert fields["skeptic_agent"] is None
    assert fields["agents"] == [
        {"name": "bot_a", "role": "default"},
        {"name": "bot_b", "role": "default"},
    ]


def test_blueprint_role_fields_exposes_wired_names():
    fields = blueprint_role_fields({
        "role": "support",
        "agents": [
            {"name": "Helper", "role": "support"},
            {"name": "Gate", "role": "tool_gate"},
            {"name": "Skeptic", "role": "skeptic"},
        ],
    })
    assert fields["role"] == "support"
    assert fields["gate_agent"] == "Gate"
    assert fields["skeptic_agent"] == "Skeptic"
    assert {row["name"]: row["role"] for row in fields["agents"]} == {
        "Helper": "support",
        "Gate": "gate",
        "Skeptic": "skeptic",
    }
