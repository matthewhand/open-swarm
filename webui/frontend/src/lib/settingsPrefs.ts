/**
 * Client-side settings-sheet preferences (REQ-19).
 *
 * Hostname override and retention mode persist in localStorage until a remotes
 * / settings API lands. Read/write is best-effort — private mode or quota
 * failures must not throw into the UI.
 */

export const HOSTNAME_OVERRIDE_KEY = 'swarm_hostname_override'
export const RETENTION_MODE_KEY = 'swarm_retention_mode'
export const BUMP_COMPLETED_KEY = 'swarm_bump_completed'
export const BUMP_COMPLETED_EVENT = 'swarm:bump-completed-changed'

export const RETENTION_MODES = ['count', 'disk', 'archive', 'trash'] as const
export type RetentionMode = (typeof RETENTION_MODES)[number]

export const RETENTION_MODE_LABELS: Record<RetentionMode, string> = {
  count: 'Count',
  disk: 'Disk',
  archive: 'Archive',
  trash: 'Trash',
}

export function isRetentionMode(value: unknown): value is RetentionMode {
  return typeof value === 'string' && (RETENTION_MODES as readonly string[]).includes(value)
}

export function loadHostnameOverride(): string {
  try {
    return localStorage.getItem(HOSTNAME_OVERRIDE_KEY) ?? ''
  } catch {
    return ''
  }
}

export function saveHostnameOverride(value: string): void {
  const trimmed = value.trim()
  try {
    if (trimmed) localStorage.setItem(HOSTNAME_OVERRIDE_KEY, trimmed)
    else localStorage.removeItem(HOSTNAME_OVERRIDE_KEY)
  } catch {
    /* persistence is best-effort */
  }
}

export function loadRetentionMode(): RetentionMode {
  try {
    const raw = localStorage.getItem(RETENTION_MODE_KEY)
    if (isRetentionMode(raw)) return raw
  } catch {
    /* fall through to default */
  }
  return 'count'
}

export function saveRetentionMode(mode: RetentionMode): void {
  if (!isRetentionMode(mode)) return
  try {
    localStorage.setItem(RETENTION_MODE_KEY, mode)
  } catch {
    /* persistence is best-effort */
  }
}

/** Browser hostname used when no override is stored. */
export function detectedHostname(): string {
  try {
    return window.location.hostname || ''
  } catch {
    return ''
  }
}

/**
 * When on (default), a finished generation moves that agent to the top of
 * the visible rail. Off: order changes only by drag.
 */
export function loadBumpCompleted(): boolean {
  try {
    const raw = localStorage.getItem(BUMP_COMPLETED_KEY)
    if (raw == null) return true
    return raw === '1' || raw === 'true'
  } catch {
    return true
  }
}

export function saveBumpCompleted(enabled: boolean): boolean {
  try {
    localStorage.setItem(BUMP_COMPLETED_KEY, enabled ? '1' : '0')
    window.dispatchEvent(
      new CustomEvent(BUMP_COMPLETED_EVENT, { detail: { enabled } }),
    )
  } catch {
    /* persistence is best-effort */
  }
  return enabled
}
