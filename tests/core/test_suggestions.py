"""REQ-85: suggestions parser, fail-soft run, as-tool attach."""

import os

from swarm.core.suggestions import (
    attach_suggestions_as_tool,
    canned_continue,
    canned_kickstart,
    parse_suggestions,
    run_suggestions,
    suggestions_payload_for_turn,
)


def test_parse_suggestions_json_object_and_list():
    assert parse_suggestions({"suggestions": ["Ask about setup", "Try a demo", "List risks"]}) == [
        "Ask about setup",
        "Try a demo",
        "List risks",
    ]
    assert parse_suggestions(["One", "Two"]) == ["One", "Two"]


def test_parse_suggestions_json_string_and_newlines():
    assert parse_suggestions('{"suggestions": ["Alpha", "Beta"]}') == ["Alpha", "Beta"]
    assert parse_suggestions("- first\n- second") == ["first", "second"]


def test_parse_suggestions_bad_or_empty_is_honest_omission():
    assert parse_suggestions(None) == []
    assert parse_suggestions("") == []
    assert parse_suggestions({"suggestions": []}) == []
    assert parse_suggestions({"nope": 1}) == []
    assert parse_suggestions("not json and no lines") == ["not json and no lines"]
    assert parse_suggestions([None, "  ", ""]) == []


def test_parse_suggestions_caps_and_dedupes():
    chips = parse_suggestions(
        ["Same", "same", "A" * 120, "Two", "Three", "Four", "Five", "Six"]
    )
    assert chips[0] == "Same"
    assert len(chips[2]) <= 80
    assert len(chips) == 5


def test_run_suggestions_test_mode_canned(monkeypatch):
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    assert run_suggestions(mode="kickstart") == canned_kickstart()
    assert run_suggestions(mode="continue", messages=[{"role": "user", "content": "Hello"}])
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)


def test_run_suggestions_fail_soft_without_agent(monkeypatch):
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    assert run_suggestions(mode="kickstart", agents=[]) == []
    assert run_suggestions(mode="continue", agents=None) == []


def test_run_suggestions_uses_suggest_fn():
    chips = run_suggestions(
        mode="kickstart",
        suggest_fn=lambda _agent, _prompt: {"suggestions": ["Ping", "Pong"]},
    )
    assert chips == ["Ping", "Pong"]


def test_run_suggestions_suggest_fn_exception_is_omission():
    def boom(_agent, _prompt):
        raise RuntimeError("no host")

    assert run_suggestions(mode="kickstart", suggest_fn=boom) == []


def test_attach_suggestions_as_tool_unwired_is_noop():
    class Coord:
        tools = []

    assert attach_suggestions_as_tool(Coord(), None).tools == []


def test_prod_run_without_agents_is_empty(monkeypatch):
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)
    assert run_suggestions(mode="kickstart", agents=None) == []
    assert run_suggestions(mode="continue", agents=[]) == []


def test_prod_run_invokes_wired_suggestions_agent(monkeypatch):
    monkeypatch.delenv("SWARM_TEST_MODE", raising=False)

    class Stub:
        role = "suggestions"
        name = "suggester"

        def suggest(self, prompt):
            assert "follow-up" in prompt or "empty" in prompt or "Suggest" in prompt
            return ["From specialist", "Second chip"]

    chips = run_suggestions(mode="kickstart", agents=[Stub()])
    assert chips == ["From specialist", "Second chip"]


def test_resolve_includes_specialist_for_cli_api_remote():
    from swarm.core.agent_roles import ROLE_SUGGESTIONS, find_role_agent
    from swarm.core.suggestions import resolve_suggestions_agents

    for consumer in ("cli_agent", "api_agent", "remote_harness"):
        roster = resolve_suggestions_agents(consumer)
        assert find_role_agent(roster, ROLE_SUGGESTIONS) is not None


def test_resolve_prefers_consumer_roster_specialist():
    from swarm.core.agent_roles import ROLE_SUGGESTIONS, find_role_agent
    from swarm.core.suggestions import resolve_suggestions_agents

    class TeamSuggest:
        role = "suggestions"
        name = "team-suggester"

    class Blueprint:
        _agents = {"worker": object(), "suggester": TeamSuggest()}

    roster = resolve_suggestions_agents("cli_agent", blueprint=Blueprint())
    found = find_role_agent(roster, ROLE_SUGGESTIONS)
    assert found is not None
    assert getattr(found, "name", "") == "team-suggester"


def test_suggestions_payload_respects_toggle(tmp_path, monkeypatch):
    monkeypatch.setenv("SWARM_AGENT_SETTINGS_PATH", str(tmp_path / "agent_settings.json"))
    monkeypatch.setenv("SWARM_TEST_MODE", "1")
    from swarm.core import agent_settings as store

    store.reset_agent_settings_cache()
    assert suggestions_payload_for_turn("worker", []) is None
    store.update_settings("worker", {"use_suggestions": True})
    kick = suggestions_payload_for_turn("worker", [])
    assert kick is not None
    assert kick["type"] == "suggestions"
    assert kick["suggestions"] == canned_kickstart()
    cont = suggestions_payload_for_turn(
        "worker",
        [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}],
    )
    assert cont is not None
    assert cont["suggestions"] == canned_continue(
        [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}]
    )
    store.reset_agent_settings_cache()
    os.environ.pop("SWARM_TEST_MODE", None)
