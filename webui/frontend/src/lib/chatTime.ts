/** Gap timestamps for the chat log. Calendar day is Australia/Sydney, not UTC. */

export const CHAT_TIME_ZONE = 'Australia/Sydney'
export const CHAT_GAP_MS = 15 * 60 * 1000

export function parseCreatedAtMs(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value !== 'string') return undefined
  const trimmed = value.trim()
  if (!trimmed) return undefined
  const asNumber = Number(trimmed)
  if (Number.isFinite(asNumber) && asNumber > 1e11) return asNumber
  const parsed = Date.parse(trimmed)
  return Number.isFinite(parsed) ? parsed : undefined
}

function partMap(
  ms: number,
  timeZone: string,
  options: Intl.DateTimeFormatOptions,
): Record<string, string> {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone, ...options }).formatToParts(
    new Date(ms),
  )
  const map: Record<string, string> = {}
  for (const part of parts) {
    if (part.type !== 'literal') map[part.type] = part.value
  }
  return map
}

export function sydneyDayKey(ms: number, timeZone: string = CHAT_TIME_ZONE): string {
  const parts = partMap(ms, timeZone, { year: 'numeric', month: '2-digit', day: '2-digit' })
  return `${parts.year}-${(parts.month || '').padStart(2, '0')}-${(parts.day || '').padStart(2, '0')}`
}

function addCalendarDays(year: number, month: number, day: number, delta: number) {
  const utc = new Date(Date.UTC(year, month - 1, day + delta))
  return {
    year: utc.getUTCFullYear(),
    month: utc.getUTCMonth() + 1,
    day: utc.getUTCDate(),
  }
}

function formatClock(ms: number, timeZone: string): string {
  const parts = partMap(ms, timeZone, {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
  const dayPeriod = (parts.dayPeriod || 'AM').replace(/\./g, '').trim().toUpperCase()
  return `${Number(parts.hour)}:${parts.minute} ${dayPeriod}`
}

/** Today 7:21 AM / Yesterday 6:54 AM / Wed 3 Sep 6:54 AM */
export function formatGapLabel(
  ms: number,
  nowMs: number = Date.now(),
  timeZone: string = CHAT_TIME_ZONE,
): string {
  const clock = formatClock(ms, timeZone)
  const day = sydneyDayKey(ms, timeZone)
  const today = sydneyDayKey(nowMs, timeZone)
  if (day === today) return `Today ${clock}`

  const todayParts = partMap(nowMs, timeZone, {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  })
  const yesterday = addCalendarDays(
    Number(todayParts.year),
    Number(todayParts.month),
    Number(todayParts.day),
    -1,
  )
  const yesterdayKey = `${yesterday.year}-${String(yesterday.month).padStart(2, '0')}-${String(yesterday.day).padStart(2, '0')}`
  if (day === yesterdayKey) return `Yesterday ${clock}`

  const stamp = partMap(ms, timeZone, {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
  return `${stamp.weekday} ${stamp.day} ${stamp.month} ${clock}`
}

export function shouldShowGapStamp(
  previousMs: number | undefined,
  nextMs: number | undefined,
  timeZone: string = CHAT_TIME_ZONE,
): boolean {
  if (previousMs == null || nextMs == null) return false
  if (!Number.isFinite(previousMs) || !Number.isFinite(nextMs)) return false
  if (nextMs - previousMs >= CHAT_GAP_MS) return true
  return sydneyDayKey(previousMs, timeZone) !== sydneyDayKey(nextMs, timeZone)
}
