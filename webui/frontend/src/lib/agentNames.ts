/** Per-agent display-name overrides (local only — not a rename API). */

export const AGENT_NAMES_STORAGE_KEY = 'swarm_agent_names'
export const AGENT_RENAME_EVENT = 'swarm:agent-rename'

export function catalogAgentName(agent: { id: string; name?: string | null }): string {
  return (agent.name || agent.id).trim() || agent.id
}

function readOverrides(): Record<string, string> {
  try {
    const raw = localStorage.getItem(AGENT_NAMES_STORAGE_KEY)
    if (!raw) return {}
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return {}
    const next: Record<string, string> = {}
    for (const [id, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (typeof value === 'string' && value.trim()) next[id] = value.trim()
    }
    return next
  } catch {
    return {}
  }
}

function writeOverrides(map: Record<string, string>) {
  try {
    if (Object.keys(map).length === 0) {
      localStorage.removeItem(AGENT_NAMES_STORAGE_KEY)
    } else {
      localStorage.setItem(AGENT_NAMES_STORAGE_KEY, JSON.stringify(map))
    }
  } catch {
    /* persistence is best-effort */
  }
}

export function loadAgentNameOverride(agentId: string): string | null {
  const value = readOverrides()[agentId]
  return value || null
}

/** Empty save clears the override so the catalog/default name returns. */
export function saveAgentNameOverride(agentId: string, value: string, fallback: string): string {
  const trimmed = value.trim()
  const catalog = fallback.trim() || agentId
  const map = readOverrides()
  if (!trimmed || trimmed === catalog) {
    delete map[agentId]
    writeOverrides(map)
    emitRename(agentId, catalog)
    return catalog
  }
  map[agentId] = trimmed
  writeOverrides(map)
  emitRename(agentId, trimmed)
  return trimmed
}

function emitRename(agentId: string, name: string) {
  try {
    window.dispatchEvent(new CustomEvent(AGENT_RENAME_EVENT, { detail: { agentId, name } }))
  } catch {
    /* tests / non-browser */
  }
}

export function displayAgentName(agent: { id: string; name?: string | null }): string {
  return loadAgentNameOverride(agent.id) || catalogAgentName(agent)
}
