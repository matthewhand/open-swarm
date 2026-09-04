/**
 * Django-backed UI preferences (REQ-144 / #540).
 *
 * Favourites + Hidden Bots load from GET /v1/preferences/ and persist on
 * change via PATCH. localStorage stays a cache: if the server bag is empty
 * and this browser already has values, import once, then the server wins.
 *
 * Unexpected / offline responses keep the local cache (do not treat a
 * blueprint list mock as "empty server").
 */

import { apiGet, apiPatch, ensureCsrfCookie } from './api'
import {
  hasHiddenAgentsStorage,
  loadHiddenAgentIds,
  loadOrSeedHiddenAgentIds,
  saveHiddenAgentIds,
} from './hiddenAgents'
import {
  hasPinnedAgentsStorage,
  loadOrSeedPinnedAgents,
  loadPinnedAgents,
  savePinnedAgents,
  type PinnedAgent,
} from './pinnedAgents'

export const USER_PREFS_PATH = '/v1/preferences/'

export interface UserPrefs {
  object: 'user_preferences'
  principal: string
  guest: boolean
  empty: boolean
  favourites: PinnedAgent[]
  hidden_agents: string[]
  values?: Record<string, unknown>
}

export type RailPrefs = {
  pins: PinnedAgent[]
  hidden: string[]
  source: 'server' | 'import' | 'local'
}

function normalizePin(value: unknown): PinnedAgent | null {
  if (typeof value === 'string' && value.length > 0) {
    return { id: value, name: value }
  }
  if (!value || typeof value !== 'object') return null
  const rec = value as { id?: unknown; name?: unknown }
  if (typeof rec.id !== 'string' || rec.id.length === 0) return null
  return {
    id: rec.id,
    name: typeof rec.name === 'string' && rec.name.length > 0 ? rec.name : rec.id,
  }
}

export function parseUserPrefs(raw: unknown): UserPrefs | null {
  if (!raw || typeof raw !== 'object') return null
  const rec = raw as Record<string, unknown>
  if (rec.object !== 'user_preferences') return null
  const pins: PinnedAgent[] = []
  const seen = new Set<string>()
  if (Array.isArray(rec.favourites)) {
    for (const item of rec.favourites) {
      const pin = normalizePin(item)
      if (!pin || seen.has(pin.id)) continue
      seen.add(pin.id)
      pins.push(pin)
    }
  }
  const hidden = Array.isArray(rec.hidden_agents)
    ? rec.hidden_agents.filter((id): id is string => typeof id === 'string' && id.length > 0)
    : []
  return {
    object: 'user_preferences',
    principal: typeof rec.principal === 'string' ? rec.principal : '',
    guest: rec.guest === true,
    empty: rec.empty === true,
    favourites: pins,
    hidden_agents: Array.from(new Set(hidden)),
    values: rec.values && typeof rec.values === 'object' ? (rec.values as Record<string, unknown>) : {},
  }
}

export function applyPrefsToLocal(prefs: { favourites: PinnedAgent[]; hidden_agents: string[] }): void {
  savePinnedAgents(prefs.favourites)
  saveHiddenAgentIds(prefs.hidden_agents)
}

export async function fetchUserPrefs(): Promise<UserPrefs | null> {
  try {
    const data = await apiGet<unknown>(USER_PREFS_PATH)
    return parseUserPrefs(data)
  } catch {
    return null
  }
}

export async function saveUserPrefs(patch: {
  favourites?: PinnedAgent[]
  hidden_agents?: string[]
}): Promise<UserPrefs | null> {
  if (patch.favourites === undefined && patch.hidden_agents === undefined) {
    return null
  }
  try {
    await ensureCsrfCookie()
    const data = await apiPatch<unknown>(USER_PREFS_PATH, patch)
    const parsed = parseUserPrefs(data)
    if (parsed && !parsed.empty) {
      applyPrefsToLocal(parsed)
    }
    return parsed
  } catch {
    return null
  }
}

export function localRailSnapshot(
  catalog: Array<{ id: string; name?: string | null }> = [],
): RailPrefs {
  const pins = hasPinnedAgentsStorage() ? loadPinnedAgents() : loadOrSeedPinnedAgents()
  const hidden = hasHiddenAgentsStorage()
    ? loadHiddenAgentIds()
    : loadOrSeedHiddenAgentIds(catalog)
  return { pins, hidden, source: 'local' }
}

/**
 * Session start: server bag wins when present; otherwise one-time import
 * of the local cache (including first-load Support / gate+skeptic seeds).
 */
export async function hydrateRailPrefs(
  catalog: Array<{ id: string; name?: string | null }> = [],
): Promise<RailPrefs> {
  const server = await fetchUserPrefs()
  if (server && !server.empty) {
    applyPrefsToLocal(server)
    return { pins: server.favourites, hidden: server.hidden_agents, source: 'server' }
  }
  const local = localRailSnapshot(catalog)
  if (server?.empty) {
    await saveUserPrefs({ favourites: local.pins, hidden_agents: local.hidden })
    return { ...local, source: 'import' }
  }
  return local
}
