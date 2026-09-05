/**
 * REQ-70: reconstruct transcript chrome from side-channel metadata.
 *
 * Model turns and UI events are stored separately. The UI rebuilds the
 * visible timeline; it does not filter chrome out of a mixed transcript.
 */

import { asTranscriptRole, isStatusRole, type ChatTranscriptRole } from './chatStatus'

export type ModelTurn = {
  role: 'user' | 'assistant' | 'tool' | 'developer'
  content: string
  ts?: string
  edited?: boolean
  seq?: number
  name?: string
}

export type UiEvent = {
  kind?: 'status' | 'info' | 'hop' | string
  role?: string
  content: string
  ts?: string
  seq?: number
}

export type ReconstructedMessage = {
  role: ChatTranscriptRole
  content: string
  ts?: string
  edited?: boolean
  kind?: string
  seq?: number
}

const MODEL_ROLES = new Set(['user', 'assistant', 'tool', 'developer'])

function isChromeRole(role: string | undefined, kind?: string): boolean {
  if (kind === 'status' || kind === 'info' || kind === 'hop') return true
  return isStatusRole(role)
}

export function parseTurn(value: unknown): ModelTurn | null {
  if (!value || typeof value !== 'object') return null
  const row = value as { role?: unknown; content?: unknown; ts?: unknown; edited?: unknown; seq?: unknown; name?: unknown }
  if (typeof row.role !== 'string' || typeof row.content !== 'string') return null
  if (!MODEL_ROLES.has(row.role) || isChromeRole(row.role)) return null
  const turn: ModelTurn = {
    role: row.role as ModelTurn['role'],
    content: row.content,
  }
  if (typeof row.ts === 'string' && row.ts) turn.ts = row.ts
  if (row.edited === true) turn.edited = true
  if (typeof row.seq === 'number' && Number.isFinite(row.seq)) turn.seq = row.seq
  if (typeof row.name === 'string' && row.name.trim()) turn.name = row.name.trim()
  return turn
}

export function parseUiEvent(value: unknown): UiEvent | null {
  if (!value || typeof value !== 'object') return null
  const row = value as { kind?: unknown; role?: unknown; content?: unknown; ts?: unknown; seq?: unknown }
  if (typeof row.content !== 'string') return null
  const kind = typeof row.kind === 'string' ? row.kind : typeof row.role === 'string' ? row.role : 'status'
  if (!isChromeRole(typeof row.role === 'string' ? row.role : undefined, kind) && kind !== 'status') {
    return null
  }
  const event: UiEvent = { kind, content: row.content, role: kind }
  if (typeof row.ts === 'string' && row.ts) event.ts = row.ts
  if (typeof row.seq === 'number' && Number.isFinite(row.seq)) event.seq = row.seq
  return event
}

/** Split a leftover mixed ``messages`` list into turns + events (safety belt). */
export function splitMixedMessages(messages: unknown[]): { turns: ModelTurn[]; ui_events: UiEvent[] } {
  const turns: ModelTurn[] = []
  const ui_events: UiEvent[] = []
  messages.forEach((value, index) => {
    const event = parseUiEvent(value)
    if (event) {
      if (event.seq === undefined) event.seq = index
      ui_events.push(event)
      return
    }
    const turn = parseTurn(value)
    if (turn) {
      if (turn.seq === undefined) turn.seq = index
      turns.push(turn)
    }
  })
  return { turns, ui_events }
}

export function reconstructTranscript(
  turns: ModelTurn[],
  uiEvents: UiEvent[],
): ReconstructedMessage[] {
  const tagged: Array<{ seq: number; order: number; kind: 'turn' | 'event'; item: ModelTurn | UiEvent }> = []
  turns.forEach((turn, index) => {
    tagged.push({
      seq: typeof turn.seq === 'number' ? turn.seq : index,
      order: index,
      kind: 'turn',
      item: turn,
    })
  })
  uiEvents.forEach((event, index) => {
    tagged.push({
      seq: typeof event.seq === 'number' ? event.seq : 1_000_000 + index,
      order: turns.length + index,
      kind: 'event',
      item: event,
    })
  })
  tagged.sort((a, b) => a.seq - b.seq || a.order - b.order)
  return tagged.map(({ kind, item }) => {
    if (kind === 'turn') {
      const turn = item as ModelTurn
      const row: ReconstructedMessage = {
        role: turn.role === 'assistant' ? 'assistant' : 'user',
        content: turn.content,
      }
      if (turn.ts) row.ts = turn.ts
      if (turn.edited) row.edited = true
      if (typeof turn.seq === 'number') row.seq = turn.seq
      return row
    }
    const event = item as UiEvent
    const row: ReconstructedMessage = {
      role: asTranscriptRole(event.role || event.kind || 'status'),
      content: event.content,
      kind: event.kind || 'status',
    }
    if (event.ts) row.ts = event.ts
    if (typeof event.seq === 'number') row.seq = event.seq
    return row
  })
}

/** Short clock for chrome timestamps (reload must show when the line occurred). */
export function formatChromeTime(ts: string | undefined): string {
  if (!ts) return ''
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return ts
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
