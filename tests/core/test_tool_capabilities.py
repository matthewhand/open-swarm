"""Tests for capability-based tool decoupling (capability -> MCP provider)."""

from swarm.core import tool_capabilities as tc


def test_normalize_requirements_forms():
    assert tc.normalize_requirements(["web_search"]) == {"web_search": "mandatory"}
    assert tc.normalize_requirements({"web_search": "optional"}) == {"web_search": "optional"}
    assert tc.normalize_requirements({"x": "weird"}) == {"x": "mandatory"}  # unknown -> mandatory
    assert tc.normalize_requirements(None) == {}


def test_servers_for_lists_non_auth_first():
    names = [s.name for s in tc.servers_for(tc.WEB_SEARCH)]
    # duckduckgo (non-auth) must come before brave-search (needs a key)
    assert names.index("duckduckgo") < names.index("brave-search")


def test_resolve_prefers_non_auth_when_both_configured():
    cfg = {"mcpServers": {
        "brave-search": {"command": "npx", "args": []},   # needs BRAVE_API_KEY
        "duckduckgo": {"command": "uvx", "args": []},      # non-auth
    }}
    res = tc.resolve_requirements({"web_search": "mandatory"}, cfg, env={})
    assert res.ok
    assert res.satisfied["web_search"] == "duckduckgo"  # non-auth wins


def test_resolve_uses_auth_provider_when_key_present_and_only_option():
    cfg = {"mcpServers": {"brave-search": {"command": "npx", "args": []}}}
    # No key -> mandatory unmet
    res = tc.resolve_requirements({"web_search": "mandatory"}, cfg, env={})
    assert not res.ok and "web_search" in res.missing_mandatory
    assert "web_search" in res.unusable
    # Key present -> satisfied
    res2 = tc.resolve_requirements({"web_search": "mandatory"}, cfg, env={"BRAVE_API_KEY": "k"})
    assert res2.ok and res2.satisfied["web_search"] == "brave-search"


def test_optional_unmet_is_skipped_not_missing():
    res = tc.resolve_requirements({"filesystem": "optional"}, {"mcpServers": {}}, env={})
    assert res.ok  # optional never blocks
    assert res.skipped_optional == ["filesystem"]
    assert not res.missing_mandatory


def test_provides_override_lets_any_server_satisfy_a_capability():
    cfg = {"mcpServers": {"my-search": {"command": "x", "args": [], "provides": ["web_search"]}}}
    res = tc.resolve_requirements(["web_search"], cfg, env={})
    assert res.satisfied["web_search"] == "my-search"


def test_playwright_is_a_non_auth_browser_provider():
    pw = tc.known_server("playwright")
    assert pw is not None and not pw.needs_auth
    assert tc.BROWSER in pw.provides
    assert tc.servers_for(tc.BROWSER)[0].name == "playwright"


def test_resolve_mcp_servers_uses_configured_provider():
    cfg = {"mcpServers": {"duckduckgo": {"command": "uvx", "args": ["duckduckgo-mcp-server"]}}}
    servers, res = tc.resolve_mcp_servers({"web_search": "mandatory"}, cfg, env={})
    assert "duckduckgo" in servers and res.ok


def test_resolve_mcp_servers_autostarts_playwright_for_browser():
    # Nothing configured; a mandatory browser need is auto-provisioned from the
    # non-auth catalog (official playwright-mcp) so it just works.
    servers, res = tc.resolve_mcp_servers({"browser": "mandatory"}, {"mcpServers": {}}, env={})
    assert "playwright" in servers
    assert servers["playwright"]["command"] == "npx"
    assert res.ok and res.satisfied["browser"] == "playwright"
    assert "env" not in servers["playwright"]  # non-auth, runnable as-is


def test_resolve_mcp_servers_can_disable_autostart():
    servers, res = tc.resolve_mcp_servers(
        {"browser": "mandatory"}, {"mcpServers": {}}, env={}, autostart_catalog=False
    )
    assert servers == {} and not res.ok


def test_suggest_mcp_config_prefers_non_auth():
    cfg = tc.suggest_mcp_config(["web_search", "filesystem"])
    servers = cfg["mcpServers"]
    assert "duckduckgo" in servers and "brave-search" not in servers  # non-auth pick
    assert "filesystem" in servers
    # non-auth server has no env block; the generated config is runnable as-is
    assert "env" not in servers["duckduckgo"]


def test_resolve_tolerates_provides_given_as_a_string():
    # A single capability given as a string (common config mistake) should still
    # provide it, not be split into characters.
    cfg = {"mcpServers": {"x": {"command": "y", "args": [], "provides": "web_search"}}}
    res = tc.resolve_requirements({"web_search": "mandatory"}, cfg, env={})
    assert res.satisfied["web_search"] == "x"
