/** Matches swarm.consumers.WS_AUTH_REQUIRED_CODE (session gate). */
export const WS_AUTH_REQUIRED_CODE = 4401

export const MAX_AUTO_RECONNECT_ATTEMPTS = 8
const BASE_MS = 1000
const MAX_MS = 16_000

/** Exponential backoff: 1s, 2s, 4s… capped at 16s. */
export function reconnectBackoffMs(attempt: number): number {
  const n = Math.max(0, Math.floor(attempt))
  return Math.min(BASE_MS * 2 ** n, MAX_MS)
}

/**
 * Auto-reconnect after unexpected closes. Skip intentional cleanup closes
 * and auth gate 4401 (session required — Sign-in CTA, no hammering).
 */
export function shouldAutoReconnect(
  code: number,
  intentional: boolean,
  attempt: number,
): boolean {
  if (intentional) return false
  if (code === WS_AUTH_REQUIRED_CODE) return false
  return attempt < MAX_AUTO_RECONNECT_ATTEMPTS
}
