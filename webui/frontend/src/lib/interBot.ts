/** Inter-bot hop status lines (Grok Bot: Messaged N Bots / Message from Name). */

export interface InterBotHop {
  id: string
  agentId: string
  name: string
  pending: boolean
}

export type InterBotLine =
  | { kind: 'progress' }
  | { kind: 'single'; hop: InterBotHop }
  | { kind: 'multi'; hops: InterBotHop[] }

export interface ChatMessageItem {
  type: 'message'
  key: string
  role: 'user' | 'assistant'
  text: string
  streaming: boolean
  createdAtMs?: number
}

export interface ChatHopItem {
  type: 'hop'
  key: string
  hop: InterBotHop
}

export type ChatItem = ChatMessageItem | ChatHopItem

export type ChatRow =
  | { type: 'message'; message: ChatMessageItem }
  | { type: 'hop-line'; line: InterBotLine; hops: InterBotHop[] }

/** `{ "assistant": "HASS" }` handoff payload used by rest-mode chat. */
export function parseHandoffAssistant(text: string): string | null {
  const trimmed = text.trim()
  if (!trimmed.startsWith('{')) return null
  try {
    const parsed = JSON.parse(trimmed) as { assistant?: unknown }
    if (typeof parsed.assistant === 'string' && parsed.assistant.trim()) {
      return parsed.assistant.trim()
    }
  } catch {
    /* not a handoff object */
  }
  return null
}

export function hopFromAssistantName(
  id: string,
  name: string,
  pending: boolean,
  agentId?: string,
): InterBotHop {
  const trimmed = name.trim()
  return {
    id,
    agentId: (agentId || trimmed).trim().toLowerCase().replace(/\s+/g, '-') || id,
    name: trimmed,
    pending,
  }
}

/**
 * Collapse one adjacent hop run.
 * Any in-flight hop → dots only (no avatars). One completed hop → Message from.
 * Two or more completed hops → Messaged N Bots.
 */
export function collapseInterBotHops(hops: InterBotHop[]): InterBotLine | null {
  if (hops.length === 0) return null
  if (hops.some((hop) => hop.pending)) return { kind: 'progress' }
  if (hops.length === 1) return { kind: 'single', hop: hops[0]! }
  return { kind: 'multi', hops }
}

/** Group sequential hops into one status line; leave chat bubbles in place. */
export function groupChatItems(items: ChatItem[]): ChatRow[] {
  const rows: ChatRow[] = []
  let buffer: InterBotHop[] = []

  const flush = () => {
    const line = collapseInterBotHops(buffer)
    if (line) rows.push({ type: 'hop-line', line, hops: buffer })
    buffer = []
  }

  for (const item of items) {
    if (item.type === 'hop') {
      buffer.push(item.hop)
      continue
    }
    flush()
    rows.push({ type: 'message', message: item })
  }
  flush()
  return rows
}
