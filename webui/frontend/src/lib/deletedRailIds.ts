/**
 * REQ-82: Delete is stronger than Hide. Deleted rail ids leave both the
 * conversation list and Hidden Bots. Persistence is localStorage, same
 * best-effort pattern as hidden / pinned.
 */

export const DELETED_RAIL_IDS_KEY = 'swarm_deleted_rail_ids'

export function parseDeletedRailIds(raw: string | null): string[] {
  if (!raw) return []
  try {
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((id): id is string => typeof id === 'string' && id.length > 0)
  } catch {
    return []
  }
}

export function loadDeletedRailIds(): string[] {
  try {
    return parseDeletedRailIds(localStorage.getItem(DELETED_RAIL_IDS_KEY))
  } catch {
    return []
  }
}

export function saveDeletedRailIds(ids: string[]): string[] {
  const unique = Array.from(new Set(ids.filter((id) => id.length > 0)))
  try {
    localStorage.setItem(DELETED_RAIL_IDS_KEY, JSON.stringify(unique))
  } catch {
    /* persistence is best-effort */
  }
  return unique
}

export function markRailIdDeleted(id: string, current: string[] = loadDeletedRailIds()): string[] {
  if (!id || current.includes(id)) return current
  return saveDeletedRailIds([...current, id])
}

export function isRailIdDeleted(id: string, current: string[] = loadDeletedRailIds()): boolean {
  return Boolean(id) && current.includes(id)
}
