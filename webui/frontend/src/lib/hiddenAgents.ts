/**
 * Persist which agents are hidden from the SPA left rail.
 *
 * Hidden IDs live in localStorage so a reload keeps the same visible list.
 * There is no hide-all control — hide is always per-agent.
 *
 * REQ-24: any conversation/agent row can be hidden, including role-assigned
 * seats (support, gate, skeptic). Hide is not exempt by role.
 *
 * Hide wins for the visible list. The rail also unpins favourite tiles when
 * an agent is hidden (removed from the list AND the pin grid). Unhide restores
 * the conversation row only — it does not re-pin.
 *
 * REQ-26: first visit (no `swarm_hidden_agents` key) seeds gate + skeptic.
 * An existing key — including `[]` after Unhide — is user customization.
 */

import {
  GATE_AGENT_ID,
  SKEPTIC_AGENT_ID,
  TOOL_GATE_AGENT_ID,
  isGateAgent,
  isSkepticAgent,
} from './supportAgent'

export const HIDDEN_AGENTS_STORAGE_KEY = 'swarm_hidden_agents'

/** Fallback ids when the live catalog has not listed a gate/skeptic seat yet. */
export const DEFAULT_HIDDEN_AGENT_IDS: readonly string[] = [
  GATE_AGENT_ID,
  TOOL_GATE_AGENT_ID,
  SKEPTIC_AGENT_ID,
]

export function hasHiddenAgentsStorage(): boolean {
  try {
    return localStorage.getItem(HIDDEN_AGENTS_STORAGE_KEY) !== null
  } catch {
    return false
  }
}

export function parseHiddenAgentIds(raw: string | null): string[] {
  if (!raw) return []
  try {
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((id): id is string => typeof id === 'string' && id.length > 0)
  } catch {
    return []
  }
}

export function loadHiddenAgentIds(): string[] {
  try {
    return parseHiddenAgentIds(localStorage.getItem(HIDDEN_AGENTS_STORAGE_KEY))
  } catch {
    return []
  }
}

/** Catalog ids that should start Hidden (whatever the catalog actually ships). */
export function defaultHiddenAgentIds(
  catalog: Array<{ id: string; name?: string | null }> = [],
): string[] {
  const fromCatalog = catalog
    .filter((agent) => isGateAgent(agent) || isSkepticAgent(agent))
    .map((agent) => agent.id)
    .filter((id) => id.length > 0)
  if (fromCatalog.length > 0) {
    return Array.from(new Set(fromCatalog))
  }
  return [...DEFAULT_HIDDEN_AGENT_IDS]
}

/**
 * First load: seed Hidden with gate + skeptic.
 * If the user already stored a list (including empty after Unhide), leave it.
 */
export function loadOrSeedHiddenAgentIds(
  catalog: Array<{ id: string; name?: string | null }> = [],
): string[] {
  if (hasHiddenAgentsStorage()) {
    return loadHiddenAgentIds()
  }
  const seeded = defaultHiddenAgentIds(catalog)
  saveHiddenAgentIds(seeded)
  return seeded
}

export function saveHiddenAgentIds(ids: string[]): void {
  const unique = Array.from(new Set(ids.filter((id) => id.length > 0)))
  try {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(unique))
  } catch {
    /* persistence is best-effort */
  }
}

export function hideAgentId(id: string, current: string[]): string[] {
  if (!id || current.includes(id)) return current
  const next = [...current, id]
  saveHiddenAgentIds(next)
  return next
}

/** Role seats (support / gate / skeptic) are hideable — no exemptions. */
export function canHideAgent(id: string): boolean {
  return typeof id === 'string' && id.length > 0
}

export function unhideAgentId(id: string, current: string[]): string[] {
  const next = current.filter((item) => item !== id)
  saveHiddenAgentIds(next)
  return next
}

/** Small muted accents for agent marks — not category-flooded buttons. */
const AGENT_MARK_COLORS = [
  '#c45c5c',
  '#c47a3a',
  '#6b8f71',
  '#4a7a9b',
  '#7a6b9b',
  '#8a6a5a',
]

export function agentMarkIndex(id: string): number {
  let hash = 0
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0
  }
  return hash % AGENT_MARK_COLORS.length
}

export function agentMarkColor(id: string): string {
  return AGENT_MARK_COLORS[agentMarkIndex(id)]
}
