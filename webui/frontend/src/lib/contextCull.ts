/**
 * REQ-121 — cache-friendly cull / start-context-from-here (API agents).
 *
 * Distinct from REQ-87 compress. Manual copy is “Start context from here.”
 * CLI is out of v1. No secrets.
 */

export const CONTEXT_STRATEGY_COMPRESS = 'compress' as const
export const CONTEXT_STRATEGY_CULL = 'cull' as const

export type ContextStrategy = typeof CONTEXT_STRATEGY_COMPRESS | typeof CONTEXT_STRATEGY_CULL

export const DEFAULT_CONTEXT_STRATEGY: ContextStrategy = CONTEXT_STRATEGY_COMPRESS
export const DEFAULT_CULL_TRIGGER_PCT = 90
export const DEFAULT_CULL_FRACTION_PCT = 50
export const MIN_CONTEXT_PCT = 1
export const MAX_CONTEXT_PCT = 99

export const START_CONTEXT_FROM_HERE_LABEL = 'Start context from here'
export const START_CONTEXT_FROM_HERE_TOOLTIP = 'Start context from here.'

export type ContextEventKind = 'cull' | 'start_from_here' | 'compress'

export interface ContextLastEvent {
  kind: ContextEventKind
  at?: string
  start_offset?: number
  culled_count?: number
  fraction_pct?: number
  estimated_pct?: number
}

export interface ContextMeta {
  start_offset: number
  last_event: ContextLastEvent | null
}

export function parseContextStrategy(raw: unknown): ContextStrategy {
  const text = typeof raw === 'string' ? raw.trim().toLowerCase() : ''
  if (text === CONTEXT_STRATEGY_CULL || text === 'cull-head' || text === 'trim') {
    return CONTEXT_STRATEGY_CULL
  }
  return CONTEXT_STRATEGY_COMPRESS
}

export function parseContextPct(raw: unknown, fallback: number): number {
  const value = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw) : NaN
  if (!Number.isFinite(value)) return fallback
  return Math.min(MAX_CONTEXT_PCT, Math.max(MIN_CONTEXT_PCT, Math.round(value)))
}

export function parseCullTriggerPct(raw: unknown): number {
  return parseContextPct(raw, DEFAULT_CULL_TRIGGER_PCT)
}

export function parseCullFractionPct(raw: unknown): number {
  return parseContextPct(raw, DEFAULT_CULL_FRACTION_PCT)
}

export function parseContextLastEvent(raw: unknown): ContextLastEvent | null {
  if (!raw || typeof raw !== 'object') return null
  const rec = raw as Record<string, unknown>
  const kind = rec.kind
  if (kind !== 'cull' && kind !== 'start_from_here' && kind !== 'compress') return null
  const event: ContextLastEvent = { kind }
  if (typeof rec.at === 'string' && rec.at.trim()) event.at = rec.at.trim()
  if (typeof rec.start_offset === 'number' && Number.isFinite(rec.start_offset)) {
    event.start_offset = rec.start_offset
  }
  if (typeof rec.culled_count === 'number' && Number.isFinite(rec.culled_count)) {
    event.culled_count = rec.culled_count
  }
  if (typeof rec.fraction_pct === 'number' && Number.isFinite(rec.fraction_pct)) {
    event.fraction_pct = rec.fraction_pct
  }
  if (typeof rec.estimated_pct === 'number' && Number.isFinite(rec.estimated_pct)) {
    event.estimated_pct = rec.estimated_pct
  }
  return event
}

export function parseContextMeta(raw: unknown): ContextMeta {
  if (!raw || typeof raw !== 'object') {
    return { start_offset: 0, last_event: null }
  }
  const rec = raw as Record<string, unknown>
  const start = typeof rec.start_offset === 'number' && Number.isFinite(rec.start_offset)
    ? Math.max(0, Math.floor(rec.start_offset))
    : 0
  return { start_offset: start, last_event: parseContextLastEvent(rec.last_event) }
}

export function lastEventLabel(event: ContextLastEvent | null | undefined): string {
  if (!event) return 'None yet'
  if (event.kind === 'start_from_here') return 'Start context from here'
  if (event.kind === 'cull') return 'Auto cull'
  return 'Compress'
}

export function strategyLabel(strategy: ContextStrategy): string {
  return strategy === CONTEXT_STRATEGY_CULL ? 'Cull' : 'Compress'
}

/** Remaining usage still ≥ cull-trigger % of a known max. Unknown max → no warning. */
export function wouldWarnAfterStart(
  estimatedTokens: number,
  contextMax: number | null | undefined,
  cullTriggerPct: number,
): boolean {
  if (contextMax == null || contextMax <= 0) return false
  const trigger = parseCullTriggerPct(cullTriggerPct)
  return estimatedTokens >= (contextMax * trigger) / 100
}

export function overFullWarningCopy(estimatedPct: number, cullTriggerPct: number): string {
  const pct = Math.round(estimatedPct)
  const trigger = parseCullTriggerPct(cullTriggerPct)
  return (
    `Starting context here still leaves usage at ${pct}% ` +
    `(cull trigger ${trigger}%). Confirm to proceed or cancel.`
  )
}
