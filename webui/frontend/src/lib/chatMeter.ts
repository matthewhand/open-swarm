/** Soft cap for the tokens-in-context meter (display only). */
export const CONTEXT_METER_TOKENS = 128_000

/** Rough in-context token count from visible transcript text (~4 chars/token). */
export function estimateTokensInContext(texts: string[]): number {
  const chars = texts.reduce((sum, text) => sum + text.length, 0)
  return Math.max(0, Math.round(chars / 4))
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
