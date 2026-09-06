"""
Contract and unit tests for REQ-169 slash catalog (skills and actions).
Verifies that slash actions and skills expected by the composer popup are
registered and discoverable in the backend.
"""

import pytest
from swarm.core.slash_commands import slash_registry
from swarm.core.skills import discover_skills


def test_core_slash_actions_registered():
    """Verify standard composer slash actions exist in slash_registry."""
    expected_actions = [
        "/compact",
        "/help",
        "/model",
        "/clear",
        "/approval",
        "/history",
    ]
    for action in expected_actions:
        fn = slash_registry.get(action)
        assert fn is not None, f"Expected action {action} to be registered in slash_registry"
        assert callable(fn)


def test_standard_skills_discoverable():
    """Verify standard skills referenced in the frontend composer catalog exist."""
    skills = discover_skills()
    expected_skills = [
        "conventional-commit",
        "counting-lines",
        "reviewing-code",
        "support-session-ownership",
        "self-update-pr",
        "writing-changelog",
    ]
    for skill_name in expected_skills:
        assert skill_name in skills, f"Expected skill {skill_name} in discovered skills"
        skill = skills[skill_name]
        assert skill.name == skill_name
        assert skill.description, f"Skill {skill_name} must have a description"
        assert skill.instructions, f"Skill {skill_name} must have instructions"


def test_compact_action_callable():
    """Verify /compact slash command returns expected error or summary string."""
    fn = slash_registry.get("/compact")
    # Calling without active context returns fallback message
    res = fn()
    assert isinstance(res, str)
    assert "compact" in res.lower()
