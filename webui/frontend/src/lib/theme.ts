export const THEME_STORAGE_KEY = 'swarm_theme'
export const THEME_SET_EVENT = 'swarm:set-theme'
export const THEME_TOGGLE_EVENT = 'swarm:toggle-theme'

export type Theme = 'dark' | 'light'

export function initialTheme(): Theme {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    /* storage unavailable — fall through to the dark default */
  }
  return 'dark'
}

export function persistTheme(theme: Theme): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    /* persistence is best-effort */
  }
}

export function dispatchSetTheme(theme: Theme): void {
  window.dispatchEvent(new CustomEvent<Theme>(THEME_SET_EVENT, { detail: theme }))
}

export function dispatchToggleTheme(): void {
  window.dispatchEvent(new CustomEvent(THEME_TOGGLE_EVENT))
}
