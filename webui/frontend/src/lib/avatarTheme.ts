/**
 * Avatar theme preference. Default keeps today's os-agent-dot marks.
 * Blobs is a Grok-Bot-style geometric set. Persist is best-effort localStorage,
 * same contract as the rail hostname override.
 */

export const AVATAR_THEME_STORAGE_KEY = 'swarm_avatar_theme'
export const AVATAR_THEME_SET_EVENT = 'swarm:set-avatar-theme'

export const AVATAR_THEMES = ['default', 'blobs'] as const
export type AvatarTheme = (typeof AVATAR_THEMES)[number]

export function isAvatarTheme(value: unknown): value is AvatarTheme {
  return value === 'default' || value === 'blobs'
}

export function defaultAvatarTheme(): AvatarTheme {
  return 'default'
}

export function loadAvatarTheme(): AvatarTheme {
  try {
    const stored = localStorage.getItem(AVATAR_THEME_STORAGE_KEY)
    if (isAvatarTheme(stored)) return stored
  } catch {
    /* storage unavailable */
  }
  return defaultAvatarTheme()
}

export function saveAvatarTheme(value: string): AvatarTheme {
  const next = isAvatarTheme(value) ? value : defaultAvatarTheme()
  try {
    if (next === defaultAvatarTheme()) {
      localStorage.removeItem(AVATAR_THEME_STORAGE_KEY)
    } else {
      localStorage.setItem(AVATAR_THEME_STORAGE_KEY, next)
    }
  } catch {
    /* persistence is best-effort */
  }
  dispatchAvatarTheme(next)
  return next
}

export function dispatchAvatarTheme(theme: AvatarTheme): void {
  try {
    window.dispatchEvent(new CustomEvent<AvatarTheme>(AVATAR_THEME_SET_EVENT, { detail: theme }))
  } catch {
    /* window unavailable */
  }
}
