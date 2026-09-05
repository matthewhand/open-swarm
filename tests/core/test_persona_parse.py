"""Static openai-agents persona parse (REQ-81 / #433). Never executes source."""

from pathlib import Path

from swarm.core.persona_parse import parse_openai_agent_personas

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "openai_agents_personas"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_three_agent_calls_return_count_and_names():
    parsed = parse_openai_agent_personas(_read("three_agents.py"))
    assert parsed["count"] == 3
    assert [p["name"] for p in parsed["personas"]] == ["Researcher", "Writer", "Reviewer"]
    assert parsed["parsed"] is True


def test_one_agent_returns_single_name():
    parsed = parse_openai_agent_personas(_read("one_agent.py"))
    assert parsed["count"] == 1
    assert parsed["personas"] == [{"name": "Solo"}]


def test_garbage_source_is_one_generic_no_invented_names():
    parsed = parse_openai_agent_personas(_read("garbage.py"))
    assert parsed["count"] == 1
    assert parsed["personas"] == []
    assert parsed["parsed"] is False
    assert "FakeInvented" not in str(parsed)


def test_make_agent_helpers_used_by_software_dev():
    parsed = parse_openai_agent_personas(_read("make_agent_software_dev.py"))
    assert parsed["count"] == 3
    assert [p["name"] for p in parsed["personas"]] == [
        "engineer",
        "skeptic",
        "coding-requirements-gate",
    ]


def test_variable_name_is_not_invented():
    source = 'name = "ShouldNotAppear"\nAgent(name=name, instructions="x")\n'
    parsed = parse_openai_agent_personas(source)
    assert parsed["count"] == 1
    assert parsed["personas"] == []


def test_does_not_execute_source():
    source = "raise SystemExit('executed')\nAgent(name='Nope')\n"
    parsed = parse_openai_agent_personas(source)
    assert parsed["personas"] == [{"name": "Nope"}]
    assert parsed["count"] == 1
