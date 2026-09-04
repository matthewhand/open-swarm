import type { ChatMessage, CompactedLine } from '../types/agent'

/** Live turns kept after compact (summary + last N). */
export const LIVE_TAIL = 3

export function linesFromMessages(messages: ChatMessage[]): CompactedLine[] {
  const lines: CompactedLine[] = []
  for (const message of messages) {
    if (message.kind === 'summary' && message.compacted?.length) {
      lines.push(...message.compacted)
      continue
    }
    if (message.streaming) continue
    lines.push({
      role: message.role,
      text: message.text,
      agent: message.agent,
    })
  }
  return lines
}

export function compactSlice(messages: ChatMessage[], hereIndex: number) {
  if (hereIndex < 0 || hereIndex >= messages.length) return null
  const keepFrom = Math.min(hereIndex, Math.max(0, messages.length - LIVE_TAIL))
  if (keepFrom <= 0) return null
  return {
    back: messages.slice(0, keepFrom),
    tail: messages.slice(keepFrom),
  }
}

export function canCompactAt(messages: ChatMessage[], hereIndex: number): boolean {
  return compactSlice(messages, hereIndex) !== null
}

export function buildSummaryPrompt(lines: CompactedLine[], steer = ''): string {
  const transcript = lines
    .map((line) => `[${line.agent || line.role}]: ${line.text}`)
    .join('\n\n')
  const extra = steer.trim() ? `\nAdditional guidance: ${steer.trim()}\n` : ''
  return (
    'Write a concise conversation summary for later context. ' +
    'Preserve names, decisions, and open tasks. ' +
    'Do not answer the user or continue the task.' +
    extra +
    `\nTranscript:\n${transcript}`
  )
}

export function makeSummaryMessage(text: string, compacted: CompactedLine[]): ChatMessage {
  return {
    key: `summary-${Date.now().toString(36)}`,
    role: 'assistant',
    text,
    agent: 'Summary',
    kind: 'summary',
    compacted,
    timestamp: new Date(),
  }
}
