### Plugins — MCP local / remote / OpenAPI servers (#502 / #750)

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

#### Add paths

| Add | Kind | What it stores |
|---|---|---|
| **Add: Local MCP** | `local` | `command`, `args`, optional `cwd`, optional env name |
| **Add: Remote MCP** | `remote` | `url` (http/s), optional header name + env |
| **Add: OpenAPI (mcp-openapi-proxy)** | `local` or `remote` + `source=openapi` | see below |

Never paste a token, key, or URL userinfo. Config ownership refuses plaintext.
Auth values are `${VAR}` only.

#### OpenAPI via mcp-openapi-proxy (#750)

Uses [matthewhand/mcp-openapi-proxy](https://github.com/matthewhand/mcp-openapi-proxy)
so OpenAPI operations become MCP tools. open-swarm does **not** vendor that
repo and does **not** invent a second OpenAPI→MCP mapper.

**v1 remote path (chosen):** the operator pastes the **running proxy MCP URL**
(SSE / streamable-HTTP as that host already exposes). open-swarm does not
launch an HTTP proxy for remote mode.

**Local path:** swarm configures stdio `uvx mcp-openapi-proxy` and sets
`OPENAPI_SPEC_URL` to the wizard spec (http(s) URL or `file://` path).

| Field | Local | Remote |
|---|---|---|
| Display name | required | required |
| OpenAPI spec source | URL or local file path (required) | optional display URL (http/s only) |
| Proxy MCP URL | — | required (`url`) |
| Auth | optional env name (`API_KEY` → `${API_KEY}`) | optional header + `${VAR}` |

Install / run for local mode (do not commit secrets; names only):

```bash
uvx mcp-openapi-proxy
# or
pip install mcp-openapi-proxy
```

Upstream env names the proxy reads (values stay in the operator environment):

- `OPENAPI_SPEC_URL` — spec URL or `file:///path/to/spec.json`
- `API_KEY` — optional API auth for the spec host
- `API_AUTH_TYPE` / `API_AUTH_HEADER` / `SERVER_URL_OVERRIDE` / `TOOL_WHITELIST`

Saved shape (local):

```json
{
  "petstore": {
    "kind": "local",
    "source": "openapi",
    "command": "uvx",
    "args": ["mcp-openapi-proxy"],
    "openapi_spec_url": "https://example.invalid/openapi.json",
    "env": {
      "OPENAPI_SPEC_URL": "https://example.invalid/openapi.json",
      "API_KEY": "${API_KEY}"
    }
  }
}
```

Honest failures: bad spec URL, local file missing, `mcp-openapi-proxy` not
installed, connect timeout. Disabled / removed servers drop their tools.

#### Discover tools

After **Save**, **Discover tools** connects (`list_tools`) and shows each tool
name + short description. Failure is an error toast, not a silent empty list.
CI uses fixture local + remote + OpenAPI mocks — no live host, no `:8001`.

#### Runtime

Enabled servers contribute their discovered tools to the API agent. Disabled
or removed servers contribute nothing. Per-chat Off still excludes a catalog
tool even when the server is enabled.

Manual post-merge verify: point at an MCP already working in Rakazo or
OpenMousBot on LAN. Do not put those URLs or secrets in Issues or PRs.
