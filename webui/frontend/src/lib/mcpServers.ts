/**
 * MCP server entries for Settings → Plugins (#502 manage path).
 *
 * Source of truth is ``swarm_config.json`` ``mcpServers`` via
 * ``/v1/mcp-plugins/``. localStorage is a write-through cache so the rail
 * Plugins popup can show configured tools when the API is mid-flight.
 *
 * Env / header values are ``${VAR}`` placeholders only — never keys or tokens.
 */

export const MCP_SERVERS_KEY = 'swarm_mcp_servers'
export const MCP_SERVERS_EVENT = 'swarm:mcp-servers'

export type McpServerKind = 'local' | 'remote'

export interface McpDiscoveredTool {
  name: string
  description: string
}

export interface McpServerEntry {
  id: string
  name: string
  kind: McpServerKind
  enabled: boolean
  command?: string
  args?: string[]
  url?: string
  cwd?: string
  env?: Record<string, string>
  headers?: Record<string, string>
  provides: string[]
  tools: McpDiscoveredTool[]
  note?: string
}

const PLACEHOLDER_RE = /^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$/
const ENV_NAME_RE = /^[A-Z][A-Z0-9_]*$/

function isKind(value: unknown): value is McpServerKind {
  return value === 'local' || value === 'remote'
}

export function isEnvPlaceholder(value: string): boolean {
  const trimmed = value.trim()
  return PLACEHOLDER_RE.test(trimmed) || ENV_NAME_RE.test(trimmed)
}

export function asEnvPlaceholder(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) return ''
  if (PLACEHOLDER_RE.test(trimmed)) return trimmed
  if (ENV_NAME_RE.test(trimmed)) return `\${${trimmed}}`
  return ''
}

function parsePlaceholderMap(value: unknown): Record<string, string> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}
  const out: Record<string, string> = {}
  for (const [key, raw] of Object.entries(value as Record<string, unknown>)) {
    const name = key.trim()
    if (!name || typeof raw !== 'string') continue
    const placeholder = asEnvPlaceholder(raw)
    if (placeholder) out[name] = placeholder
  }
  return out
}

function parseTools(value: unknown): McpDiscoveredTool[] {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => {
      if (!item || typeof item !== 'object') return null
      const row = item as Record<string, unknown>
      const name = typeof row.name === 'string' ? row.name.trim() : ''
      if (!name) return null
      return {
        name,
        description: typeof row.description === 'string' ? row.description.trim() : '',
      }
    })
    .filter((row): row is McpDiscoveredTool => row !== null)
}

function parseEntry(value: unknown): McpServerEntry | null {
  if (!value || typeof value !== 'object') return null
  const row = value as Record<string, unknown>
  const id = typeof row.id === 'string' && row.id.trim()
    ? row.id.trim()
    : typeof row.name === 'string'
      ? row.name.trim()
      : ''
  const name =
    (typeof row.label === 'string' && row.label.trim()) ||
    (typeof row.name === 'string' ? row.name.trim() : id)
  const kind = isKind(row.kind)
    ? row.kind
    : typeof row.url === 'string' && row.url.trim()
      ? 'remote'
      : 'local'
  if (!id || !name) return null
  const provides = Array.isArray(row.provides)
    ? row.provides.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    : []
  const args = Array.isArray(row.args)
    ? row.args.filter((item): item is string => typeof item === 'string')
    : []
  const tools = parseTools(row.tools ?? row.discovered_tools)
  return {
    id,
    name,
    kind,
    enabled: row.enabled !== false && row.enabled !== 'false',
    command: typeof row.command === 'string' ? row.command : '',
    args,
    url: typeof row.url === 'string' ? row.url : '',
    cwd: typeof row.cwd === 'string' ? row.cwd : '',
    env: parsePlaceholderMap(row.env),
    headers: parsePlaceholderMap(row.headers),
    provides: provides.length > 0 ? provides : tools.map((tool) => tool.name),
    tools,
    note: typeof row.note === 'string' ? row.note : '',
  }
}

export function loadConfiguredMcpServers(): McpServerEntry[] {
  try {
    const raw = localStorage.getItem(MCP_SERVERS_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.map(parseEntry).filter((row): row is McpServerEntry => row !== null)
  } catch {
    return []
  }
}

export function saveConfiguredMcpServers(servers: readonly McpServerEntry[]): McpServerEntry[] {
  const next = servers.map(parseEntry).filter((row): row is McpServerEntry => row !== null)
  try {
    localStorage.setItem(MCP_SERVERS_KEY, JSON.stringify(next))
  } catch {
    /* private mode */
  }
  try {
    window.dispatchEvent(new CustomEvent(MCP_SERVERS_EVENT, { detail: { servers: next } }))
  } catch {
    /* jsdom / SSR */
  }
  return next
}

export function upsertMcpServer(entry: McpServerEntry): McpServerEntry[] {
  const parsed = parseEntry(entry)
  if (!parsed) return loadConfiguredMcpServers()
  const current = loadConfiguredMcpServers().filter((row) => row.id !== parsed.id)
  return saveConfiguredMcpServers([...current, parsed])
}

export function removeMcpServer(id: string): McpServerEntry[] {
  return saveConfiguredMcpServers(loadConfiguredMcpServers().filter((row) => row.id !== id))
}

export function serversFromApi(payload: { servers?: unknown } | null | undefined): McpServerEntry[] {
  const rows = Array.isArray(payload?.servers) ? payload.servers : []
  return rows
    .map(parseEntry)
    .filter((row): row is McpServerEntry => row !== null)
}

export function entryToUpsertBody(entry: McpServerEntry): Record<string, unknown> {
  const parsed = parseEntry(entry)
  if (!parsed) return {}
  const body: Record<string, unknown> = {
    name: parsed.name || parsed.id,
    kind: parsed.kind,
    enabled: parsed.enabled,
    provides: parsed.provides,
    note: parsed.note || '',
  }
  if (parsed.kind === 'remote') {
    body.url = parsed.url || ''
    if (parsed.headers && Object.keys(parsed.headers).length > 0) {
      body.headers = parsed.headers
    }
  } else {
    body.command = parsed.command || ''
    body.args = parsed.args || []
    if (parsed.cwd) body.cwd = parsed.cwd
    if (parsed.env && Object.keys(parsed.env).length > 0) {
      body.env = parsed.env
    }
  }
  if (parsed.tools.length > 0) {
    body.discovered_tools = parsed.tools
  }
  return body
}

/** Catalog templates operators can add without pasting secrets. */
export const MCP_SERVER_TEMPLATES: Omit<McpServerEntry, 'id' | 'enabled' | 'tools'>[] = [
  {
    name: 'DuckDuckGo',
    kind: 'local',
    command: 'uvx',
    args: ['duckduckgo-mcp-server'],
    provides: ['web_search'],
    note: 'Non-auth web search.',
  },
  {
    name: 'Fetch',
    kind: 'local',
    command: 'uvx',
    args: ['mcp-server-fetch'],
    provides: ['web_fetch'],
    note: 'Non-auth URL fetch.',
  },
  {
    name: 'Playwright',
    kind: 'local',
    command: 'npx',
    args: ['-y', '@playwright/mcp@latest'],
    provides: ['browser_navigate', 'browser_snapshot', 'browser_click'],
    note: 'Local browser tools.',
  },
  {
    name: 'Filesystem',
    kind: 'local',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-filesystem'],
    provides: ['read_file', 'write_file', 'list_directory'],
    note: 'Scoped local files. No keys.',
  },
  {
    name: 'Git',
    kind: 'local',
    command: 'uvx',
    args: ['mcp-server-git'],
    provides: ['git_status', 'git_diff', 'git_log'],
    note: 'Non-auth local git.',
  },
  {
    name: 'Time',
    kind: 'local',
    command: 'uvx',
    args: ['mcp-server-time'],
    provides: ['get_current_time', 'convert_timezone'],
    note: 'Non-auth time/timezone.',
  },
]

export function newMcpServerId(name: string): string {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
  return slug || `mcp-${Date.now().toString(36)}`
}
