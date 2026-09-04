"""Decision question fence — laconic, parseable, not a system pill."""

from swarm.core.decision_question import (
    format_decision_question,
    parse_decision_question,
    strip_decision_question,
)


def test_format_and_parse_round_trip():
    text = format_decision_question(
        ask="Configure which agent?",
        choices=["hybrid_team", "skeptic"],
        other="Name an agent",
        question_id="configure-agent",
    )
    assert text.startswith("```question\n")
    parsed = parse_decision_question(text)
    assert parsed == {
        "id": "configure-agent",
        "ask": "Configure which agent?",
        "choices": ["hybrid_team", "skeptic"],
        "other": "Name an agent",
    }
    assert strip_decision_question(f"note\n{text}\n") == "note"


def test_parse_rejects_empty_choices_and_prose():
    assert parse_decision_question("Just a wall of prose?") is None
    assert parse_decision_question("```question\n{\"ask\":\"x\",\"choices\":[]}\n```") is None
