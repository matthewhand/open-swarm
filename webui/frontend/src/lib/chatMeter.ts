/** Soft cap for the tokens-in-context meter when the model max is unknown (display only). */
export const CONTEXT_METER_TOKENS = 128_000

export const CONTEXT_LENGTH_KEYS = [
  'context_length',
  'context_window',
  'max_context',
  'max_context_tokens',
] as const

/** Rough in-context token count from visible transcript text (~4 chars/token). */
export function estimateTokensInContext(texts: string[]): number {
  const chars = texts.reduce((sum, text) => sum + text.length, 0)
  return Math.max(0, Math.round(chars / 4))
}

/** Read a known context window from a profile / inference entry. Never guess 128k. */
export function resolveContextMax(entry: unknown): number | null {
  if (!entry || typeof entry !== 'object') return null
  const rec = entry as Record<string, unknown>
  for (const key of CONTEXT_LENGTH_KEYS) {
    const raw = rec[key]
    const value = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw) : NaN
    if (Number.isFinite(value) && value > 0) return Math.round(value)
  }
  return null
}

export function resolveContextMaxFromProfiles(
  profiles: Array<{ id?: string; model?: string; context_length?: number; context_window?: number; max_context?: number }> | undefined,
  modelId: string | undefined,
): number | null {
  const ident = (modelId || '').trim()
  if (!ident || !profiles?.length) return null
  const match = profiles.find((row) => row.id === ident || row.model === ident)
  return match ? resolveContextMax(match) : null
}

export function formatMeterLabel(used: number, max: number | null): string {
  if (max != null && max > 0) {
    return `${formatTokenCount(used)} / ${formatTokenCount(max)} tok`
  }
  return `${formatTokenCount(used)} tok`
}

export function formatTokenCount(n: number): string {
  if (n < 1000) return String(n)
  if (n < 10_000) return `${(n / 1000).toFixed(1)}k`
  return `${Math.round(n / 1000)}k`
}

export function formatElapsed(ms: number): string {
  const sec = Math.max(0, Math.floor(ms / 1000))
  if (sec < 60) return `${sec}s`
  const minutes = Math.floor(sec / 60)
  const rem = sec % 60
  return `${minutes}m ${String(rem).padStart(2, '0')}s`
}

/** Stable per-agent conversation id so switching agents does not reuse a thread. */
const conversationByAgent = new Map<string, string>()

export function conversationIdForAgent(
  agentId: string,
  mint: () => string,
): string {
  const key = agentId || 'support'
  const existing = conversationByAgent.get(key)
  if (existing) return existing
  const minted = mint()
  conversationByAgent.set(key, minted)
  return minted
}

/** Test helper — do not use in product code. */
export function resetConversationThreads(): void {
  conversationByAgent.clear()
}
