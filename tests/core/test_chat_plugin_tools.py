"""Per-chat plugin allowlist (#805) — Off catalog tools are excluded."""

from types import SimpleNamespace

from swarm.core.chat_plugin_tools import (
    apply_chat_plugin_allowlist,
    filter_plugin_tools_for_chat,
)


def _fn(name: str):
    return SimpleNamespace(name=name, __name__=name)


def test_filter_drops_off_catalog_tools_and_keeps_native():
    functions = [_fn("web_search"), _fn("native_summarize"), _fn("git_status")]
    kept = filter_plugin_tools_for_chat(functions, ["web_search"])
    assert [fn.name for fn in kept] == ["web_search", "native_summarize"]


def test_empty_allowlist_excludes_all_catalog_tools():
    functions = [_fn("web_fetch"), _fn("answer")]
    kept = filter_plugin_tools_for_chat(functions, [])
    assert [fn.name for fn in kept] == ["answer"]


def test_apply_allowlist_filters_blueprint_agents():
    agent = SimpleNamespace(functions=[_fn("read_file"), _fn("chat")], tools=[_fn("write_file")])
    blueprint = SimpleNamespace(agents={"worker": agent}, starting_agent=agent)
    apply_chat_plugin_allowlist(blueprint, ["read_file"])
    assert [fn.name for fn in agent.functions] == ["read_file", "chat"]
    assert agent.tools == []
