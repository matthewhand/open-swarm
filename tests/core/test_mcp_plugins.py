"""#502 Plugins MCP manage — local/remote normalize, discover mocks, runtime."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from swarm.core.mcp_plugins import (
    McpPluginError,
    apply_plugin_mcp_runtime,
    attach_plugin_mcp_tools,
    enabled_mcp_servers,
    list_tools_for_spec,
    normalize_plugin_spec,
    plugin_catalog_ids,
    public_server,
)


def _fn(name: str):
    return SimpleNamespace(name=name, __name__=name)


def test_normalize_local_and_remote():
    local = normalize_plugin_spec(
        {"name": "Fetch", "kind": "local", "command": "uvx", "args": ["mcp-server-fetch"]},
        name="Fetch",
    )
    assert local["kind"] == "local"
    assert local["command"] == "uvx"
    assert local["args"] == ["mcp-server-fetch"]
    assert local["enabled"] is True

    remote = normalize_plugin_spec(
        {
            "name": "proxy",
            "kind": "remote",
            "url": "https://example.invalid/mcp",
            "headers": {"Authorization": "${MCP_TOKEN}"},
        },
        name="proxy",
    )
    assert remote["kind"] == "remote"
    assert remote["url"] == "https://example.invalid/mcp"
    assert remote["headers"]["Authorization"] == "${MCP_TOKEN}"


def test_refuse_plaintext_env_and_url_userinfo():
    with pytest.raises(McpPluginError) as env_err:
        normalize_plugin_spec(
            {"name": "bad", "command": "uvx", "env": {"API_KEY": "sk-live"}},
            name="bad",
        )
    assert env_err.value.code == "plaintext_secret"

    with pytest.raises(McpPluginError) as url_err:
        normalize_plugin_spec(
            {"name": "bad", "kind": "remote", "url": "https://user:token@example.invalid/mcp"},
            name="bad",
        )
    assert url_err.value.code == "plaintext_secret"


def test_list_tools_local_and_remote_mocks():
    def local_fn(spec):
        assert spec["kind"] == "local"
        assert spec["command"] == "uvx"
        return [{"name": "fetch", "description": "Fetch a URL"}]

    tools = list_tools_for_spec(
        {"name": "fetch", "kind": "local", "command": "uvx", "args": ["mcp-server-fetch"]},
        list_tools_fn=local_fn,
    )
    assert tools == [{"name": "fetch", "description": "Fetch a URL"}]

    def remote_fn(spec):
        assert spec["kind"] == "remote"
        assert spec["url"] == "https://example.invalid/mcp"
        return [{"name": "search", "description": "Search docs"}]

    tools = list_tools_for_spec(
        {"name": "proxy", "kind": "remote", "url": "https://example.invalid/mcp"},
        list_tools_fn=remote_fn,
    )
    assert tools[0]["name"] == "search"


def test_list_tools_disabled_refuses():
    with pytest.raises(McpPluginError) as exc:
        list_tools_for_spec(
            {"name": "fetch", "command": "uvx", "enabled": False},
            list_tools_fn=lambda _spec: [{"name": "fetch"}],
        )
    assert exc.value.code == "disabled"


def test_public_server_redacts_and_lists_tools():
    row = public_server(
        "brave",
        {
            "command": "npx",
            "env": {"BRAVE_API_KEY": "${BRAVE_API_KEY}"},
            "discovered_tools": [{"name": "brave_web_search", "description": "Search the web"}],
        },
    )
    blob = str(row)
    assert "sk-" not in blob
    assert row["tools"][0]["name"] == "brave_web_search"
    assert row["env"]["BRAVE_API_KEY"] == "${BRAVE_API_KEY}"


def test_disable_removes_tools_from_agent():
    config = {
        "mcpServers": {
            "fetch": {
                "command": "uvx",
                "args": ["mcp-server-fetch"],
                "discovered_tools": [{"name": "web_fetch", "description": "Fetch a URL"}],
            },
            "time": {
                "command": "uvx",
                "args": ["mcp-server-time"],
                "enabled": False,
                "discovered_tools": [{"name": "get_current_time", "description": "Now"}],
            },
        }
    }
    agent = SimpleNamespace(functions=[_fn("chat")], tools=[], mcp_servers=[])
    blueprint = SimpleNamespace(agents={"worker": agent}, starting_agent=agent)
    attach_plugin_mcp_tools(blueprint, config)
    names = [getattr(fn, "name", "") for fn in agent.functions]
    assert "web_fetch" in names
    assert "get_current_time" not in names
    assert "time" not in enabled_mcp_servers(config)

    apply_plugin_mcp_runtime(blueprint, config, [])
    names = [getattr(fn, "name", "") for fn in agent.functions]
    assert "web_fetch" not in names
    assert "chat" in names


def test_plugin_catalog_ids_include_discovered():
    ids = plugin_catalog_ids(
        {
            "mcpServers": {
                "custom": {
                    "command": "uvx",
                    "discovered_tools": [{"name": "acme_lookup", "description": "Lookup"}],
                }
            }
        }
    )
    assert "acme_lookup" in ids
    assert "web_search" in ids
