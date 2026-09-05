/**
 * Local MCP server entries for Settings → Plugins (#502 manage path).
 *
 * Document store only (localStorage). No API keys, tokens, or env values —
 * command/URL shape plus capability tags. Live attach is still #502.
 */

export const MCP_SERVERS_KEY = 'swarm_mcp_servers'
export const MCP_SERVERS_EVENT = 'swarm:mcp-servers'

export type McpServerKind = 'local' | 'remote'

export interface McpServerEntry {
  id: string
  name: string
  kind: McpServerKind
  command?: string
  args?: string[]
  url?: string
  provides: string[]
  note?: string
}

function isKind(value: unknown): value is McpServerKind {
  return value === 'local' || value === 'remote'
}

function parseEntry(value: unknown): McpServerEntry | null {
  if (!value || typeof value !== 'object') return null
  const row = value as Record<string, unknown>
  const id = typeof row.id === 'string' ? row.id.trim() : ''
  const name = typeof row.name === 'string' ? row.name.trim() : ''
  if (!id || !name || !isKind(row.kind)) return null
  const provides = Array.isArray(row.provides)
    ? row.provides.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    : []
  const args = Array.isArray(row.args)
    ? row.args.filter((item): item is string => typeof item === 'string')
    : []
  return {
    id,
    name,
    kind: row.kind,
    command: typeof row.command === 'string' ? row.command : '',
    args,
    url: typeof row.url === 'string' ? row.url : '',
    provides,
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

/** Catalog templates operators can add without pasting secrets. */
export const MCP_SERVER_TEMPLATES: Omit<McpServerEntry, 'id'>[] = [
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
