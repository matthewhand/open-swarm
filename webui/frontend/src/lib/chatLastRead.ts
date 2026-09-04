import { agentIdFromBlueprint } from './agentChat'

/** Last-read cursor per agent conversation (message count when the thread was opened). */
export const LAST_READ_STORAGE_KEY = 'swarm_chat_last_read'

export interface ChatLastRead {
  conversationId: string
  messageCount: number
}

function readStore(): Record<string, ChatLastRead> {
  try {
    const raw = localStorage.getItem(LAST_READ_STORAGE_KEY)
    if (!raw) return {}
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return {}
    const next: Record<string, ChatLastRead> = {}
    for (const [id, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (!value || typeof value !== 'object') continue
      const row = value as { conversationId?: unknown; messageCount?: unknown }
      if (typeof row.conversationId !== 'string' || !row.conversationId) continue
      if (typeof row.messageCount !== 'number' || !Number.isFinite(row.messageCount)) continue
      next[id] = {
        conversationId: row.conversationId,
        messageCount: Math.max(0, Math.floor(row.messageCount)),
      }
    }
    return next
  } catch {
    return {}
  }
}

function writeStore(map: Record<string, ChatLastRead>) {
  try {
    if (Object.keys(map).length === 0) {
      localStorage.removeItem(LAST_READ_STORAGE_KEY)
    } else {
      localStorage.setItem(LAST_READ_STORAGE_KEY, JSON.stringify(map))
    }
  } catch {
    /* persistence is best-effort */
  }
}

export function loadLastRead(
  agentId: string,
  conversationId: string,
): ChatLastRead | null {
  const row = readStore()[agentIdFromBlueprint(agentId)]
  if (!row || row.conversationId !== conversationId) return null
  return row
}

export function saveLastRead(
  agentId: string,
  conversationId: string,
  messageCount: number,
): ChatLastRead {
  const map = readStore()
  const row: ChatLastRead = {
    conversationId,
    messageCount: Math.max(0, Math.floor(messageCount)),
  }
  map[agentIdFromBlueprint(agentId)] = row
  writeStore(map)
  return row
}
