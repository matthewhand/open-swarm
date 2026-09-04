"""Support Socratic configure questions — other agents, not Support itself."""

from swarm.core.support_socratic import (
    other_agent_choices,
    socratic_configure_question,
    wants_configure,
)
from swarm.core.decision_question import parse_decision_question


def test_wants_configure_is_narrow():
    assert wants_configure("configure skeptic tools")
    assert wants_configure("set the prompt on hybrid_team")
    assert not wants_configure("write a blueprint")
    assert not wants_configure("")


def test_other_agent_choices_skip_support():
    names = other_agent_choices(
        {
            "agents": [
                {"id": "support", "name": "Support", "role": "support"},
                {"id": "hybrid_team", "name": "Hybrid Team", "role": ""},
                {"id": "skeptic", "name": "Skeptic", "role": "skeptic"},
            ]
        }
    )
    assert "Support" not in names
    assert "Hybrid Team" in names
    assert "Skeptic" in names


def test_socratic_steps_are_one_card():
    ctx = {
        "agents": [
            {"id": "support", "name": "Support", "role": "support"},
            {"id": "hybrid_team", "name": "hybrid_team", "role": ""},
        ]
    }
    first = parse_decision_question(socratic_configure_question("configure an agent", ctx))
    assert first is not None
    assert first["ask"] == "Configure which agent?"
    assert "hybrid_team" in first["choices"]
    assert "Support" not in first["choices"]
    assert first["other"] == "Name an agent"

    facet = parse_decision_question(
        socratic_configure_question("configure hybrid_team", ctx)
    )
    assert facet["ask"] == "hybrid_team — tools or prompt?"
    assert facet["choices"] == ["Tools", "Prompt"]

    tools = parse_decision_question(
        socratic_configure_question("hybrid_team tools", ctx)
    )
    assert tools["ask"] == "hybrid_team tools — add which?"
    assert "Files" in tools["choices"]

    prompt = parse_decision_question(
        socratic_configure_question("hybrid_team prompt", ctx)
    )
    assert prompt["ask"] == "hybrid_team prompt — tone?"
