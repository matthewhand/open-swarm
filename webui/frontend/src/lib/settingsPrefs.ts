/**
 * Client-side settings-sheet preferences (REQ-19).
 *
 * Hostname override and retention mode persist in localStorage until a remotes
 * / settings API lands. Read/write is best-effort — private mode or quota
 * failures must not throw into the UI.
 */

export const HOSTNAME_OVERRIDE_KEY = 'swarm_hostname_override'
export const RETENTION_MODE_KEY = 'swarm_retention_mode'

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
