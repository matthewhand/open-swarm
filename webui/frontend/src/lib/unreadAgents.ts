/**
 * REQ-210: Unread blue dot (replaces timestamp) + Mark as unread.
 *
 * Persists unread agent seat IDs in localStorage ('swarm_unread_agents').
 * Dispatches 'swarm:unread-changed' on mutation so rail and other UI components update.
 */

export const UNREAD_AGENTS_STORAGE_KEY = 'swarm_unread_agents'
export const UNREAD_CHANGED_EVENT = 'swarm:unread-changed'

export function parseUnreadAgentIds(raw: string | null): string[] {
  if (!raw) return []
  try {
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((id): id is string => typeof id === 'string' && id.length > 0)
  } catch {
    return []
  }
}

export function loadUnreadAgentIds(): string[] {
  try {
    return parseUnreadAgentIds(localStorage.getItem(UNREAD_AGENTS_STORAGE_KEY))
  } catch {
    return []
  }
}

export function saveUnreadAgentIds(ids: string[]): string[] {
  const unique = Array.from(new Set(ids.filter((id) => typeof id === 'string' && id.length > 0)))
  try {
    localStorage.setItem(UNREAD_AGENTS_STORAGE_KEY, JSON.stringify(unique))
  } catch {
    /* storage quota / unavailable */
  }
  try {
    window.dispatchEvent(
      new CustomEvent(UNREAD_CHANGED_EVENT, { detail: { unreadIds: unique } }),
    )
  } catch {
    /* non-browser environment */
  }
  return unique
}

export function isAgentUnread(id: string, currentUnread?: string[]): boolean {
  if (!id) return false
  const list = currentUnread ?? loadUnreadAgentIds()
  return list.includes(id)
}

export function markAgentUnread(id: string): string[] {
  if (!id) return loadUnreadAgentIds()
  const current = loadUnreadAgentIds()
  if (current.includes(id)) return current
  return saveUnreadAgentIds([...current, id])
}

export function markAgentRead(id: string): string[] {
  if (!id) return loadUnreadAgentIds()
  const current = loadUnreadAgentIds()
  if (!current.includes(id)) return current
  return saveUnreadAgentIds(current.filter((item) => item !== id))
}

export function toggleAgentUnread(id: string): string[] {
  if (!id) return loadUnreadAgentIds()
  const current = loadUnreadAgentIds()
  if (current.includes(id)) {
    return markAgentRead(id)
  }
  return markAgentUnread(id)
}
