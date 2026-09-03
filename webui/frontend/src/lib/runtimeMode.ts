/**
 * REQ-45 runtime banner: where the *app* is running.
 * Dismissed state persists in localStorage (same best-effort pattern as hostname).
 */

export const RUNTIME_BANNER_STORAGE_KEY = 'swarm_runtime_banner_dismissed'

export const RUNTIME_MODES = ['bare-metal', 'sandbox-home', 'sandbox-isolated', 'unknown'] as const

export type RuntimeMode = (typeof RUNTIME_MODES)[number]
export type RuntimeTone = 'warning' | 'info' | 'unknown'

export interface RuntimeBannerPayload {
  mode: RuntimeMode
  known: boolean
  tone: RuntimeTone
  title: string
  message: string
  env_var?: string
}

const UNKNOWN_BANNER: RuntimeBannerPayload = {
  mode: 'unknown',
  known: false,
  tone: 'unknown',
  title: 'Runtime mode unknown',
  message:
    'SWARM_RUNTIME_MODE is unset or unrecognized. This instance is not claiming to be isolated — never assume a green sandbox. Set bare-metal, sandbox-home, or sandbox-isolated.',
}

export function isRuntimeMode(value: unknown): value is RuntimeMode {
  return typeof value === 'string' && (RUNTIME_MODES as readonly string[]).includes(value)
}

export function parseRuntimeBanner(raw: unknown): RuntimeBannerPayload {
  if (!raw || typeof raw !== 'object') return UNKNOWN_BANNER
  const body = raw as Record<string, unknown>
  if (!isRuntimeMode(body.mode)) return UNKNOWN_BANNER
  const tone: RuntimeTone =
    body.tone === 'warning' || body.tone === 'info' || body.tone === 'unknown' ? body.tone : 'unknown'
  // Missing env / unknown must never render as isolated green.
  if (body.mode === 'unknown' && tone === 'info') {
    return { ...UNKNOWN_BANNER }
  }
  if (typeof body.title !== 'string' || typeof body.message !== 'string') {
    return { ...UNKNOWN_BANNER, mode: body.mode, known: body.mode !== 'unknown' }
  }
  return {
    mode: body.mode,
    known: body.mode !== 'unknown',
    tone: body.mode === 'unknown' ? 'unknown' : tone,
    title: body.title,
    message: body.message,
    env_var: typeof body.env_var === 'string' ? body.env_var : undefined,
  }
}

export function loadDismissedRuntimeMode(): RuntimeMode | null {
  try {
    const stored = localStorage.getItem(RUNTIME_BANNER_STORAGE_KEY)
    if (isRuntimeMode(stored)) return stored
  } catch {
    /* storage unavailable */
  }
  return null
}

export function saveDismissedRuntimeMode(mode: RuntimeMode): void {
  try {
    localStorage.setItem(RUNTIME_BANNER_STORAGE_KEY, mode)
  } catch {
    /* persistence is best-effort */
  }
}

export function clearDismissedRuntimeMode(): void {
  try {
    localStorage.removeItem(RUNTIME_BANNER_STORAGE_KEY)
  } catch {
    /* persistence is best-effort */
  }
}

export function isRuntimeBannerDismissed(mode: RuntimeMode): boolean {
  return loadDismissedRuntimeMode() === mode
}
