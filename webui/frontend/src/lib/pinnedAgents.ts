/**
 * Persist pinned agent shortcuts (drag-from-sidebar tiles).
 *
 * This is a copy/pin, not a move: the AGENTS sidepane row stays.
 * IDs live in localStorage so a reload keeps the same unlabeled top grid.
 */

export const PINNED_AGENTS_STORAGE_KEY = 'swarm_pinned_agents'
export const AGENT_DRAG_MIME = 'application/x-swarm-agent'

export interface PinnedAgent {
  id: string
  name: string
}

let activeDrag: PinnedAgent | null = null

export function beginAgentDrag(agent: PinnedAgent): void {
  if (!agent.id) {
    activeDrag = null
    return
  }
  activeDrag = { id: agent.id, name: agent.name || agent.id }
}

export function endAgentDrag(): void {
  activeDrag = null
}

export function peekAgentDrag(): PinnedAgent | null {
  return activeDrag
}

export function loadPinnedAgents(): PinnedAgent[] {
  try {
    const raw = localStorage.getItem(PINNED_AGENTS_STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    const seen = new Set<string>()
    const pins: PinnedAgent[] = []
    for (const item of parsed) {
      const pin = normalizePin(item)
      if (!pin || seen.has(pin.id)) continue
      seen.add(pin.id)
      pins.push(pin)
    }
    return pins
  } catch {
    return []
  }
}

export function savePinnedAgents(pins: PinnedAgent[]): void {
  const unique: PinnedAgent[] = []
  const seen = new Set<string>()
  for (const item of pins) {
    const pin = normalizePin(item)
    if (!pin || seen.has(pin.id)) continue
    seen.add(pin.id)
    unique.push(pin)
  }
  try {
    localStorage.setItem(PINNED_AGENTS_STORAGE_KEY, JSON.stringify(unique))
  } catch {
    /* persistence is best-effort */
  }
}

export function pinAgent(agent: PinnedAgent, current: PinnedAgent[]): PinnedAgent[] {
  const pin = normalizePin(agent)
  if (!pin) return current
  if (current.some((item) => item.id === pin.id)) return current
  const next = [...current, pin]
  savePinnedAgents(next)
  return next
}

export function unpinAgent(id: string, current: PinnedAgent[]): PinnedAgent[] {
  if (!id) return current
  const next = current.filter((item) => item.id !== id)
  savePinnedAgents(next)
  return next
}

export function writeAgentDragPayload(dataTransfer: DataTransfer, agent: PinnedAgent): void {
  const pin = normalizePin(agent)
  if (!pin) return
  beginAgentDrag(pin)
  try {
    dataTransfer.setData(AGENT_DRAG_MIME, JSON.stringify(pin))
    dataTransfer.setData('text/plain', pin.id)
    dataTransfer.effectAllowed = 'copy'
  } catch {
    /* some test DataTransfers only implement a subset */
  }
}

export function parseAgentDragPayload(dataTransfer?: DataTransfer | null): PinnedAgent | null {
  const fromSession = peekAgentDrag()
  if (fromSession) return fromSession
  if (!dataTransfer) return null
  try {
    const typed = dataTransfer.getData(AGENT_DRAG_MIME)
    if (typed) {
      const pin = normalizePin(JSON.parse(typed) as unknown)
      if (pin) return pin
    }
  } catch {
    /* fall through to text/plain */
  }
  try {
    const plain = dataTransfer.getData('text/plain')
    return normalizePin(plain)
  } catch {
    return null
  }
}

function normalizePin(value: unknown): PinnedAgent | null {
  if (typeof value === 'string' && value.length > 0) {
    return { id: value, name: value }
  }
  if (!value || typeof value !== 'object') return null
  const record = value as { id?: unknown; name?: unknown }
  if (typeof record.id !== 'string' || record.id.length === 0) return null
  const name = typeof record.name === 'string' && record.name.length > 0 ? record.name : record.id
  return { id: record.id, name }
}
