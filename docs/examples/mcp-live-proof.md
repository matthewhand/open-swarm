### Live MCP proof — capability → auto-provisioned non-auth server → tools

`scripts/prove_mcp_live.py` resolves a capability to a concrete MCP server via
`tool_capabilities.resolve_mcp_servers` (auto-provisioning the non-auth catalog
provider with zero config), then **launches it over stdio and lists its tools** —
proving the resolved config is live, not just well-formed.

```
capability 'web_fetch' -> fetch: uvx mcp-server-fetch
  handshake OK — 1 tools exposed
  sample: fetch
LIVE MCP PROOF: PASS

capability 'browser' -> playwright: npx -y @playwright/mcp@latest
  handshake OK — 23 tools exposed
  sample: browser_close, browser_navigate, browser_fill_form, browser_evaluate, ...
LIVE MCP PROOF: PASS
```

A blueprint that declares `tool_requirements = {"browser": "mandatory"}` gets the
official **microsoft/playwright-mcp** wired in automatically — no API key, no
config. Both `jeeves` and `whiskeytango_foxtrot` declare browser needs this way.
