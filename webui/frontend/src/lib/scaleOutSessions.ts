/**
 * REQ-66 / REQ-65: per-agent scale-out sessions (new chat per task).
 *
 * One rail row per agent. When that agent has more than one session the
 * row stacks avatars and opens a search-palette picker. Persistence is
 * localStorage so #393 can mint sessions without a new REST surface.
 */

export const SCALE_OUT_SESSIONS_STORAGE_KEY = 'swarm_scale_out_sessions'
export const SCALE_OUT_SESSIONS_EVENT = 'swarm:scale-out-sessions'
/** Matches `.os-scale-out-pulse` period so delays stay in-phase with motion. */
export const SCALE_OUT_PULSE_MS = 1400
/** Rail stack shows this many faces; extras become a +N remainder. */
export const STACKED_AVATAR_MAX = 3

export type AgentSessionStatus = 'running' | 'finished'

export interface AgentSession {
  id: string
  agentId: string
  title: string
  snippet: string
  status: AgentSessionStatus
  /** Epoch ms when the session started. Drives stacked-avatar stagger. */
  startedAt: number
  updatedAt: number
}

export interface StackedAvatarPlan {
  faces: AgentSession[]
  remainder: number
  delaysMs: number[]
}

function isStatus(value: unknown): value is AgentSessionStatus {
  return value === 'running' || value === 'finished'
}

function isSession(value: unknown): value is AgentSession {
  if (!value || typeof value !== 'object') return false
  const row = value as Partial<AgentSession>
  return (
    typeof row.id === 'string' &&
    row.id.length > 0 &&
    typeof row.agentId === 'string' &&
    row.agentId.length > 0 &&
    typeof row.title === 'string' &&
    typeof row.snippet === 'string' &&
    isStatus(row.status) &&
    typeof row.startedAt === 'number' &&
    Number.isFinite(row.startedAt) &&
    typeof row.updatedAt === 'number' &&
    Number.isFinite(row.updatedAt)
  )
}

function parseStore(raw: string | null): Record<string, AgentSession[]> {
  if (!raw) return {}
  try {
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
    const out: Record<string, AgentSession[]> = {}
    for (const [agentId, rows] of Object.entries(parsed as Record<string, unknown>)) {
      if (!agentId || !Array.isArray(rows)) continue
      const sessions = rows.filter(isSession).map((row) => ({
        ...row,
        agentId: row.agentId || agentId,
      }))
      if (sessions.length) out[agentId] = sessions
    }
    return out
  } catch {
    return {}
  }
}

function emitSessionsChanged(): void {
  try {
    window.dispatchEvent(new CustomEvent(SCALE_OUT_SESSIONS_EVENT))
  } catch {
    /* jsdom / SSR */
  }
}

export function loadAllAgentSessions(): Record<string, AgentSession[]> {
  try {
    return parseStore(localStorage.getItem(SCALE_OUT_SESSIONS_STORAGE_KEY))
  } catch {
    return {}
  }
}

export function saveAllAgentSessions(store: Record<string, AgentSession[]>): void {
  const clean: Record<string, AgentSession[]> = {}
  for (const [agentId, rows] of Object.entries(store)) {
    const sessions = rows.filter(isSession)
    if (sessions.length) clean[agentId] = sessions
  }
  try {
    localStorage.setItem(SCALE_OUT_SESSIONS_STORAGE_KEY, JSON.stringify(clean))
  } catch {
    /* persistence is best-effort */
  }
  emitSessionsChanged()
}

export function listAgentSessions(agentId: string): AgentSession[] {
  const id = (agentId || '').trim()
  if (!id) return []
  const rows = loadAllAgentSessions()[id] ?? []
  return [...rows].sort(compareSessions)
}

/** Running first, then newest activity. */
export function compareSessions(a: AgentSession, b: AgentSession): number {
  if (a.status !== b.status) return a.status === 'running' ? -1 : 1
  return b.updatedAt - a.updatedAt
}

export function saveAgentSessions(agentId: string, sessions: AgentSession[]): void {
  const id = (agentId || '').trim()
  if (!id) return
  const store = loadAllAgentSessions()
  const next = sessions.filter(isSession).map((row) => ({ ...row, agentId: id }))
  if (next.length) store[id] = next
  else delete store[id]
  saveAllAgentSessions(store)
}

export function upsertAgentSession(session: AgentSession): AgentSession[] {
  const current = listAgentSessions(session.agentId)
  const next = [session, ...current.filter((row) => row.id !== session.id)]
  saveAgentSessions(session.agentId, next)
  return listAgentSessions(session.agentId)
}

/** v1: picker only when this agent already has more than one session. */
export function shouldOpenSessionPicker(sessions: readonly AgentSession[]): boolean {
  return sessions.length > 1
}

export function filterAgentSessions(
  sessions: readonly AgentSession[],
  query: string,
): AgentSession[] {
  const q = query.trim().toLowerCase()
  if (!q) return [...sessions]
  return sessions.filter(
    (row) =>
      row.title.toLowerCase().includes(q) || row.snippet.toLowerCase().includes(q),
  )
}

export function sessionHref(agentId: string, sessionId: string): string {
  const params = new URLSearchParams()
  params.set('blueprint', agentId)
  params.set('session', sessionId)
  return `/chat?${params.toString()}`
}

/**
 * Phase offset for the shared pulse. Different `startedAt` values land on
 * different points in the 1.4s loop so stacked faces do not lockstep.
 */
export function stackAvatarDelayMs(
  startedAt: number,
  origin = 0,
  periodMs = SCALE_OUT_PULSE_MS,
): number {
  const period = periodMs > 0 ? periodMs : SCALE_OUT_PULSE_MS
  const delta = startedAt - origin
  return ((delta % period) + period) % period
}

export function stackedAvatarPlan(
  sessions: readonly AgentSession[],
  maxFaces = STACKED_AVATAR_MAX,
): StackedAvatarPlan {
  const running = sessions.filter((row) => row.status === 'running').sort(compareSessions)
  const ordered = running.length > 0 ? running : [...sessions].sort(compareSessions)
  const cap = Math.max(0, maxFaces)
  const faces = ordered.slice(0, cap)
  const remainder = Math.max(0, ordered.length - faces.length)
  const origin = faces.reduce(
    (min, row) => Math.min(min, row.startedAt),
    faces[0]?.startedAt ?? 0,
  )
  const delaysMs = faces.map((row) => stackAvatarDelayMs(row.startedAt, origin))
  return { faces, remainder, delaysMs }
}
