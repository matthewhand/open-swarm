/**
 * Local hop prefs (summary vs full + token budget). No secrets.
 */

export type HopMode = 'summary' | 'full'

export const HOP_PREFS_KEY = 'swarm_session_hop'
export const DEFAULT_HOP_MODE: HopMode = 'summary'
export const DEFAULT_HOP_TOKEN_BUDGET = 4000
export const FULL_HOP_TOKEN_BUDGET = 16_000

export type SessionHopPrefs = {
  mode: HopMode
  tokenBudget: number
}

export function parseHopMode(raw: unknown): HopMode {
  const text = String(raw || '').trim().toLowerCase()
  if (text === 'full') return 'full'
  return DEFAULT_HOP_MODE
}

export function parseTokenBudget(raw: unknown, mode: HopMode = DEFAULT_HOP_MODE): number {
  const n = Number(raw)
  if (Number.isFinite(n) && n >= 64 && n <= 128_000) return Math.floor(n)
  return mode === 'full' ? FULL_HOP_TOKEN_BUDGET : DEFAULT_HOP_TOKEN_BUDGET
}

export function loadHopPrefs(): SessionHopPrefs {
  try {
    const raw = localStorage.getItem(HOP_PREFS_KEY)
    if (!raw) return { mode: DEFAULT_HOP_MODE, tokenBudget: DEFAULT_HOP_TOKEN_BUDGET }
    const parsed = JSON.parse(raw) as { mode?: unknown; tokenBudget?: unknown }
    const mode = parseHopMode(parsed.mode)
    return { mode, tokenBudget: parseTokenBudget(parsed.tokenBudget, mode) }
  } catch {
    return { mode: DEFAULT_HOP_MODE, tokenBudget: DEFAULT_HOP_TOKEN_BUDGET }
  }
}

export function saveHopPrefs(prefs: Partial<SessionHopPrefs>): SessionHopPrefs {
  const current = loadHopPrefs()
  const next: SessionHopPrefs = {
    mode: prefs.mode ? parseHopMode(prefs.mode) : current.mode,
    tokenBudget:
      prefs.tokenBudget !== undefined
        ? parseTokenBudget(prefs.tokenBudget, prefs.mode || current.mode)
        : current.tokenBudget,
  }
  try {
    localStorage.setItem(HOP_PREFS_KEY, JSON.stringify(next))
  } catch {
    /* private mode / quota */
  }
  return next
}
