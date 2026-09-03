/**
 * Configured remotes for the AGENTS rail (REQ-68).
 *
 * Reads GET /v1/remotes/ only. Never health-probes or operate() — those hit
 * live LAN. Compatible with remotes opt-in (#384): default catalog rows
 * without agents stay off the rail.
 *
 * UI label for the omb kind is OpenMousBot, never OMB.
 */

import { parseStartedAt } from './avatarStack'

export const REMOTES_URL = '/v1/remotes/'
export const OPENMOUSBOT_LABEL = 'OpenMousBot'
export const OPENMOUSBOT_IDS = new Set(['omb', 'openmousbot', 'openmausbot'])

export interface RemoteAgent {
  id: string
  name: string
  role?: string
  started_at?: string
  startedAt?: number
  working?: boolean
  status?: 'running' | 'finished'
  snippet?: string
}

export interface RemoteEntry {
  id: string
  kind: string
  title: string
  configured: boolean
  agents: RemoteAgent[]
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

/** Public label. Internal ids may stay `omb`. */
export function remoteDisplayName(remote: {
  id?: string
  title?: string
  name?: string
  kind?: string
}): string {
  const id = String(remote.id || remote.kind || '').trim().toLowerCase()
  if (OPENMOUSBOT_IDS.has(id)) return OPENMOUSBOT_LABEL
  const raw = String(remote.title || remote.name || remote.id || '').trim()
  if (!raw) return 'Remote'
  if (OPENMOUSBOT_IDS.has(raw.toLowerCase()) || /^omb$/i.test(raw) || /openmausbot/i.test(raw)) {
    return OPENMOUSBOT_LABEL
  }
  return raw
}

export function remoteHideId(remoteId: string): string {
  return `remote:${remoteId}`
}

function parseAgent(raw: unknown, index: number): RemoteAgent | null {
  const rec = asRecord(raw)
  if (!rec) return null
  const id = typeof rec.id === 'string' ? rec.id.trim() : ''
  if (!id) return null
  const name =
    typeof rec.name === 'string' && rec.name.trim()
      ? rec.name.trim()
      : remoteDisplayName({ id, title: typeof rec.title === 'string' ? rec.title : '' })
  const role = typeof rec.role === 'string' ? rec.role : undefined
  const started =
    rec.started_at ?? rec.startedAt ?? rec.created_at ?? rec.updated_at ?? index
  const status = rec.status === 'running' || rec.status === 'finished' ? rec.status : undefined
  const snippet = typeof rec.snippet === 'string' ? rec.snippet : undefined
  return {
    id,
    name,
    role,
    started_at: typeof rec.started_at === 'string' ? rec.started_at : undefined,
    startedAt: parseStartedAt(started, index),
    working: rec.working === true || status === 'running',
    status,
    snippet,
  }
}

function agentList(rec: Record<string, unknown>): unknown[] {
  if (Array.isArray(rec.agents)) return rec.agents
  if (Array.isArray(rec.bots)) return rec.bots
  if (Array.isArray(rec.members)) return rec.members
  if (Array.isArray(rec.workers)) return rec.workers
  return []
}

export function parseRemote(raw: unknown): RemoteEntry | null {
  const rec = asRecord(raw)
  if (!rec) return null
  if (rec.object === 'blueprint' || rec.object === 'team_roster' || rec.object === 'team') {
    return null
  }
  const id = typeof rec.id === 'string' ? rec.id.trim() : ''
  if (!id) return null
  const source = typeof rec.source === 'string' ? rec.source : ''
  const configured =
    rec.configured === true || (source !== '' && source !== 'default')
  const kind =
    typeof rec.kind === 'string' && rec.kind.trim()
      ? rec.kind.trim()
      : id
  const title = remoteDisplayName({
    id,
    kind,
    title: typeof rec.title === 'string' ? rec.title : undefined,
    name: typeof rec.name === 'string' ? rec.name : undefined,
  })
  const agents = agentList(rec)
    .map((row, index) => parseAgent(row, index))
    .filter((row): row is RemoteAgent => row !== null)
  return { id, kind, title, configured, agents }
}

/** Only remotes the operator added, or that already report agents/bots. */
export function isRailRemote(remote: RemoteEntry): boolean {
  return remote.configured || remote.agents.length > 0
}

export function parseRemotes(payload: unknown): RemoteEntry[] {
  if (Array.isArray(payload)) {
    return payload.map(parseRemote).filter((row): row is RemoteEntry => row !== null)
  }
  const rec = asRecord(payload)
  if (!rec) return []
  const list = Array.isArray(rec.data) ? rec.data : null
  if (!list) return []
  return list.map(parseRemote).filter((row): row is RemoteEntry => row !== null)
}

export function parseRailRemotes(payload: unknown): RemoteEntry[] {
  return parseRemotes(payload).filter(isRailRemote)
}

/**
 * GET /v1/remotes/ — list only. Empty on auth/network/unexpected shape.
 * Does not POST health or operate (no live LAN).
 */
export async function fetchConfiguredRemotes(): Promise<RemoteEntry[]> {
  try {
    const response = await fetch(REMOTES_URL, { headers: { Accept: 'application/json' } })
    if (!response.ok) return []
    return parseRailRemotes(await response.json())
  } catch {
    return []
  }
}
