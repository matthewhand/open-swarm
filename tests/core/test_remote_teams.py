"""Remote agentic frameworks listed as Swarm agents."""

import json
from unittest.mock import patch

import pytest

from swarm.core.remote_teams import (
    catalog_frameworks,
    chat_remote,
    completions_url,
    default_remote_member,
    is_chief_of_staff_name,
    launch_dsh,
    listed_remote_specs,
    normalize_framework,
    parent_spec_for_framework,
    ollama_launch_supports,
    parse_remote_catalog,
    remote_child_id,
)
from swarm.core.router_designs import validate_design


def test_normalize_aliases():
    assert normalize_framework("OpenMausBot") == "openmausbot"
    assert normalize_framework("openmousbot") == "openmausbot"
    assert normalize_framework("rakoza") == "rakazo"
    assert normalize_framework("rakezo") == "rakazo"
    assert normalize_framework("nemohermes") == "hermes"
    assert normalize_framework("dsh") == "dsh"
    assert normalize_framework("deepseek-harness") == "dsh"
    assert normalize_framework("deepseekharness") == "dsh"


def test_catalog_includes_requested_frameworks():
    ids = {f["id"] for f in catalog_frameworks()}
    assert {"hermes", "openmausbot", "rakazo", "herdr", "dsh"} <= ids


def test_parent_spec_for_framework_uses_config_url():
    spec = parent_spec_for_framework("hermes", {
        "remote_teams": {"hermes": {"base_url": "http://10.0.0.36:9119/v1"}},
    })
    assert spec is not None
    assert spec["framework"] == "hermes"
    assert spec["base_url"] == "http://10.0.0.36:9119/v1"
    assert parent_spec_for_framework("") is None


def test_listed_specs_always_include_catalog():
    specs = listed_remote_specs({})
    ids = {s["agent_id"] for s in specs}
    assert {"hermes", "openmausbot", "rakazo", "herdr", "dsh"} <= ids
    assert all(s["kind"] == "remote" and s["group"] == "remote" for s in specs)
    assert all(s.get("agent_type") == "remote" for s in specs)


def test_listed_specs_env_url_and_no_invented_ports(monkeypatch):
    monkeypatch.setenv("HERMES_BASE_URL", "http://10.0.0.36:9119/v1")
    monkeypatch.delenv("RAKAZO_BASE_URL", raising=False)
    monkeypatch.delenv("RAKEZO_BASE_URL", raising=False)
    monkeypatch.delenv("OPENMAUSBOT_BASE_URL", raising=False)
    specs = listed_remote_specs({})
    hermes = next(s for s in specs if s["agent_id"] == "hermes")
    rakazo = next(s for s in specs if s["agent_id"] == "rakazo")
    omb = next(s for s in specs if s["agent_id"] == "openmausbot")
    assert hermes["base_url"] == "http://10.0.0.36:9119/v1"
    assert rakazo["base_url"] == ""
    assert omb["base_url"] == ""


def test_listed_specs_overlay_herdr_target():
    specs = listed_remote_specs({
        "remote_teams": {"herdr": {"target": "w2:p1"}},
    })
    herdr = next(s for s in specs if s["agent_id"] == "herdr")
    assert herdr["target"] == "w2:p1"


def test_parse_remote_catalog_shapes():
    swarm = parse_remote_catalog({
        "data": {"agents": {
            "researcher": {"name": "Researcher", "description": "facts"},
            "coder": {"name": "Coder"},
        }}
    })
    ids = {m["id"] for m in swarm}
    assert ids == {"researcher", "coder"}

    omb = parse_remote_catalog({"bots": [{"id": "night", "name": "Night editor"}]})
    assert omb[0]["id"] == "night" and omb[0]["name"] == "Night editor"

    openai = parse_remote_catalog({"data": [{"id": "hermes-agent", "object": "model"}]})
    assert openai[0]["id"] == "hermes-agent"

    rakazo = parse_remote_catalog({"agents": [{"id": "bot-1", "name": "Desk"}]})
    assert rakazo[0]["name"] == "Desk"


def test_expand_http_children_from_catalog(monkeypatch):
    from swarm.core import remote_teams as rt

    rt._DISCOVERY_CACHE.clear()
    monkeypatch.setattr(
        rt,
        "discover_http_members",
        lambda base_url, framework: [
            {"id": "hermes-agent", "name": "Hermes Agent", "description": ""},
            {"id": "research", "name": "Research profile", "description": "facts"},
        ],
    )
    specs = listed_remote_specs({
        "remote_teams": {"hermes": {"base_url": "http://127.0.0.1:9/v1"}},
    }, expand=True)
    ids = {s["agent_id"] for s in specs}
    assert "hermes" in ids
    assert "hermes--hermes-agent" in ids
    assert "hermes--research" in ids
    child = next(s for s in specs if s["agent_id"] == "hermes--research")
    assert child["parent_id"] == "hermes"
    assert child["model"] == "research"
    assert child["base_url"] == "http://127.0.0.1:9/v1"
    hermes = next(s for s in specs if s["agent_id"] == "hermes")
    assert "2 live" in hermes["specialty"]


def test_expand_rakazo_bots(monkeypatch):
    from swarm.core import remote_teams as rt

    rt._DISCOVERY_CACHE.clear()

    def fake_get(url, **kwargs):
        assert "/api/bots" in url
        return {"bots": [{"id": "desk", "name": "Desk bot"}]}

    monkeypatch.setattr(rt, "_http_get_json", fake_get)
    specs = listed_remote_specs({
        "remote_teams": {"rakazo": {"base_url": "http://10.0.0.32:9000/v1"}},
    }, expand=True)
    child = next(s for s in specs if s["agent_id"] == "rakazo--desk")
    assert child["name"] == "Desk bot"
    assert child["framework"] == "rakazo"
    assert child["model"] == "desk"


def test_expand_herdr_panes(monkeypatch):
    from swarm.core import remote_teams as rt

    monkeypatch.setattr(
        rt,
        "herdr_list_agents",
        lambda **kwargs: [
            {"pane_id": "w3:p1", "agent": "grok", "agent_status": "idle", "cwd": "/tmp"},
        ],
    )
    specs = listed_remote_specs({}, expand=True)
    child = next(s for s in specs if s["agent_id"] == "herdr--w3-p1")
    assert child["target"] == "w3:p1"
    assert child["name"] == "grok (w3:p1)"
    assert child["parent_id"] == "herdr"


def test_openmausbot_defaults_to_chief_of_staff():
    assert is_chief_of_staff_name("Chief of Staff")
    assert is_chief_of_staff_name("CoS")
    assert is_chief_of_staff_name("chief-of-staff")
    assert is_chief_of_staff_name("chiefOfStaff")
    members = [
        {"id": "night", "name": "Night editor"},
        {"id": "cos-1", "name": "Chief of Staff"},
    ]
    assert default_remote_member("openmausbot", members) == "cos-1"
    assert default_remote_member("hermes", members) == "night"
    assert default_remote_member("openmausbot", []) == ""


def test_remote_child_id_slug():
    assert remote_child_id("herdr", "w3:p1") == "herdr--w3-p1"
    assert remote_child_id("hermes", "Hermes Agent") == "hermes--hermes-agent"


def test_listed_specs_overlay_config_url():
    specs = listed_remote_specs({
        "remote_teams": {
            "hermes": {"base_url": "http://10.0.0.36:9119/v1", "model": "local"},
        }
    })
    hermes = next(s for s in specs if s["agent_id"] == "hermes")
    assert hermes["base_url"] == "http://10.0.0.36:9119/v1"
    assert hermes["model"] == "local"


def test_completions_url_and_scheme_guard():
    assert completions_url("http://10.0.0.1:9/v1").endswith("/v1/chat/completions")
    with pytest.raises(ValueError, match="http"):
        completions_url("file:///etc/passwd")


def test_dsh_default_url_and_launch_noop_under_pytest():
    specs = listed_remote_specs({})
    dsh = next(s for s in specs if s["agent_id"] == "dsh")
    assert dsh["base_url"] == "http://127.0.0.1:3080/v1"
    result = launch_dsh()
    assert result["ok"] is False
    assert "pytest" in result["error"]


def test_ollama_launch_supports_parses_help():
    help_text = "Supported integrations:\n  claude\n  dsh          DeepSeek Harness\n  hermes\n"
    assert ollama_launch_supports("dsh", help_text=help_text)
    assert ollama_launch_supports("hermes", help_text=help_text)
    assert not ollama_launch_supports("dsh", help_text="  hermes\n  claude\n")


def test_validate_remote_design():
    spec = validate_design({
        "kind": "remote",
        "name": "OpenMausBot",
        "framework": "openmausbot",
        "base_url": "http://10.0.0.32:8802/v1",
    })
    assert spec["kind"] == "remote"
    assert spec["group"] == "remote"
    assert spec["framework"] == "openmausbot"


def test_herdr_alias_and_target_split():
    from swarm.core.remote_teams import format_herdr_roster, resolve_herdr_target

    assert normalize_framework("herd") == "herdr"
    live = [{"pane_id": "w7:p1", "agent": "gemini", "agent_status": "idle", "cwd": "/tmp"}]
    target, prompt = resolve_herdr_target("w7:p1 please review", "", live)
    assert target == "w7:p1"
    assert prompt == "please review"
    target, prompt = resolve_herdr_target("hello", "w2:p1", live)
    assert target == "w2:p1" and prompt == "hello"
    roster = format_herdr_roster(live)
    assert "w7:p1" in roster and "gemini" in roster


def test_chat_herdr_prompt_then_read():
    from swarm.core.remote_teams import chat_herdr

    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)

        class P:
            returncode = 0
            stdout = "ok output" if "read" in argv else '{"ok":true}'
            stderr = ""
        return P()

    with patch("swarm.core.remote_teams.herdr_bin", return_value="/usr/bin/herdr"):
        text = chat_herdr("do the thing", target="w7:p1", timeout_ms=1000, runner=fake_run)
    assert text == "ok output"
    assert any("prompt" in c for c in calls)
    assert any("read" in c for c in calls)


def test_chat_remote_parses_openai_payload():
    class _Resp:
        def read(self):
            return json.dumps({
                "choices": [{"message": {"content": "hello from hermes"}}]
            }).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    class _Opener:
        def open(self, req, timeout=0):
            assert req.full_url.endswith("/v1/chat/completions")
            return _Resp()

    with patch("swarm.core.remote_teams.urllib.request.build_opener", return_value=_Opener()):
        text = chat_remote("http://127.0.0.1:9/v1", [{"role": "user", "content": "hi"}])
    assert text == "hello from hermes"
