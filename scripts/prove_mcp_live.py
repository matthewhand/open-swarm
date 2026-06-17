#!/usr/bin/env python3
"""Prove a capability resolves to a real, runnable non-auth MCP server.

Resolves a capability (default: browser) to a concrete MCP server config via
``tool_capabilities.resolve_mcp_servers`` (auto-provisioning the non-auth
catalog provider), then actually launches it over stdio and lists its tools —
proving the resolved config is live, not just well-formed. No API keys.

Run:  DJANGO_DEBUG=true python scripts/prove_mcp_live.py [capability]
"""
import asyncio
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
os.environ.setdefault("DJANGO_DEBUG", "true")
import django  # noqa: E402

django.setup()

from agents.mcp import MCPServerStdio  # noqa: E402

from swarm.core import tool_capabilities as tc  # noqa: E402

CAP = sys.argv[1] if len(sys.argv) > 1 else tc.BROWSER


async def main() -> int:
    # Blueprint declares a capability; we resolve it to a runnable server.
    servers, res = tc.resolve_mcp_servers({CAP: "mandatory"}, {"mcpServers": {}}, env={})
    if not res.ok or not servers:
        print(f"FAIL: could not resolve a non-auth provider for '{CAP}'")
        return 1
    name, cfg = next(iter(servers.items()))
    print(f"capability '{CAP}' -> {name}: {cfg['command']} {' '.join(cfg['args'])}")

    server = MCPServerStdio(
        name=name,
        params={"command": cfg["command"], "args": cfg["args"]},
        cache_tools_list=True,
    )
    try:
        async with server:  # launches the process + MCP handshake
            tools = await server.list_tools()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: launching/handshaking {name}: {type(e).__name__}: {str(e)[:160]}")
        return 1

    names = [t.name for t in tools]
    print(f"  handshake OK — {len(names)} tools exposed")
    print(f"  sample: {', '.join(names[:8])}")
    ok = len(names) > 0
    print(f"LIVE MCP PROOF: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
