### Plugins — MCP local / remote servers (#502)

Settings → **Plugins** (Manage servers from the rail Plugins popup) is the
configuration overlay for attaching MCP tool servers. Chat stays mounted.
This is swarm as an **MCP client**. It is distinct from `ENABLE_MCP_SERVER`
(exposing swarm *as* an MCP server on `/mcp/`).

Rail **Plugins** remains the #805 quick-toggle sheet (search + per-chat On/Off).
This page is the Manage / config path.

#### Scope (v1)

- **Servers** are global host topology in `swarm_config.json` `mcpServers`.
- **Tools** are per-chat opt-in via the rail popup (`params.enabled_tools`).
- CLI path already mounts the same `mcpServers` through `cli_mcp` when the
  catalog CLI accepts `--mcp-config`.

#### Local vs remote

| Kind | Fields | Auth |
|---|---|---|
| **Local** | `command`, `args`, optional `cwd`, optional env name | env values are `${VAR}` only |
| **Remote** | `url` (http/s), optional header name + env | header values are `${VAR}` only |

Never paste a token, key, or URL userinfo. Config ownership refuses plaintext.

#### Discover tools

After **Save**, **Discover tools** connects (`list_tools`) and shows each tool
name + short description. Failure is an error toast, not a silent empty list.
CI uses fixture local + remote mocks — no live host, no `:8001`.

#### Runtime

Enabled servers contribute their discovered tools to the API agent. Disabled
or removed servers contribute nothing. Per-chat Off still excludes a catalog
tool even when the server is enabled.

Manual post-merge verify: point at an MCP already working in Rakazo or
OpenMousBot on LAN. Do not put those URLs or secrets in Issues or PRs.
