/**
 * REQ-92 — CLI session-start status sits immediately before that turn's reply.
 *
 * Shared by the live WS reducer and hydrate so stream + reload keep one order.
 * Resume / same-session turns must not invent a "Started a new …" line.
 */

export const CLI_SESSION_NOTICE_RE =
  /^(Started a new|Resumed) \S+ session\.?$/i

export function isCliSessionNoticeText(text: string | null | undefined): boolean {
  return CLI_SESSION_NOTICE_RE.test(String(text || '').trim())
}

export function isNewCliSessionNoticeText(text: string | null | undefined): boolean {
  return /^Started a new \S+ session\.?$/i.test(String(text || '').trim())
}

type TranscriptRow = {
  role: string
  text?: string
  content?: string
}

function rowText(row: TranscriptRow): string {
  return String(row.text ?? row.content ?? '').trim()
}

function lastUserIndex(messages: TranscriptRow[]): number {
  let last = -1
  for (let i = 0; i < messages.length; i += 1) {
    if (messages[i]?.role === 'user') last = i
  }
  return last
}

export function transcriptAlreadyHasNotice<T extends TranscriptRow>(
  messages: T[],
  text: string,
): boolean {
  const needle = text.trim()
  if (!needle) return false
  const lastUser = lastUserIndex(messages)
  return messages
    .slice(lastUser + 1)
    .some((row) => row.role === 'status' && rowText(row) === needle)
}

/** Insert a CLI session notice immediately before this turn's assistant row. */
export function insertCliSessionNotice<T extends TranscriptRow>(
  messages: T[],
  notice: T,
): T[] {
  const text = rowText(notice)
  if (!isCliSessionNoticeText(text)) {
    return [...messages, notice]
  }
  if (transcriptAlreadyHasNotice(messages, text)) {
    return messages
  }
  const lastUser = lastUserIndex(messages)
  const assistantIdx = messages.findIndex(
    (row, index) => index > lastUser && row.role === 'assistant',
  )
  if (assistantIdx === -1) {
    return [...messages, notice]
  }
  return [...messages.slice(0, assistantIdx), notice, ...messages.slice(assistantIdx)]
}
