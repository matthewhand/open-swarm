### Plugins popup — per-chat tool toggles (#805)

Rail **Plugins** opens a search palette (same chrome family as agent search /
session picker) over the still-mounted chat. Each row is a discovered tool
with a visible **On/Off** switch scoped to the **current conversation**.
Enabled tools sort first; search keeps that order inside matches.

**Manage servers** opens Settings → Plugins (#502 add/edit). Server entries
are local document-store rows (name, command/URL, capability tags). No API
keys, tokens, or env values are stored or shown.

#### Discovery degrade

Live MCP `list_tools` is not required for this sheet. If `GET /v1/config-options/`
has no `mcp_catalog`, or the request fails, the SPA uses the shipped fixture
catalog in `webui/frontend/src/lib/chatPluginTools.ts` so toggle / sort /
search stay real. The popup says so: “Showing the shipped catalog until MCP
servers are connected.”

On send, Chat includes `params.enabled_tools` (the On ids). Catalog tools
that are Off are excluded; blueprint-native tools that are not in the catalog
stay available.
