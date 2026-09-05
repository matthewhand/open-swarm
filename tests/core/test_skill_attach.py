"""REQ-212: attach SKILL.md skills to API / Blueprint message lists."""

from swarm.core.skill_attach import (
    apply_skills_to_messages,
    blueprint_applies_own_skills,
)


def test_blueprint_applies_own_skills_for_cli_and_support():
    assert blueprint_applies_own_skills("cli_agent")
    assert blueprint_applies_own_skills("support")
    assert not blueprint_applies_own_skills("chatbot")
    assert not blueprint_applies_own_skills("api_agent")


def test_apply_skills_to_messages_prepends_bundled_skill():
    messages = [
        {"role": "system", "content": "hi"},
        {"role": "user", "content": "write the commit"},
    ]
    out, applied, missing = apply_skills_to_messages(
        messages, {"skills": ["conventional-commit"]}
    )
    assert applied == ["conventional-commit"]
    assert missing == []
    assert out[0]["content"] == "hi"
    assert "Conventional Commit" in out[1]["content"]
    assert out[1]["content"].rstrip().endswith("write the commit")


def test_apply_skills_to_messages_missing_is_honest():
    messages = [{"role": "user", "content": "go"}]
    out, applied, missing = apply_skills_to_messages(
        messages, {"skill": "nope-not-real"}
    )
    assert applied == []
    assert missing == ["nope-not-real"]
    assert out[0]["content"] == "go"


def test_apply_skills_to_messages_applies_one_or_more():
    messages = [{"role": "user", "content": "task"}]
    out, applied, missing = apply_skills_to_messages(
        messages,
        {"skills": ["conventional-commit", "writing-changelog", "missing-skill"]},
    )
    assert applied == ["conventional-commit", "writing-changelog"]
    assert missing == ["missing-skill"]
    assert "Conventional Commit" in out[0]["content"]
    assert "changelog" in out[0]["content"].lower()
