/**
 * Platform-aware shortcut labels for quiet in-field hints (REQ-160 / #571).
 * Dismissible overlay chrome is gone — Search and composer carry the tips.
 */

export function isMacPlatform(): boolean {
  if (typeof navigator === 'undefined') return false
  return /Mac|iPod|iPhone|iPad/.test(navigator.platform || navigator.userAgent)
}

export function searchShortcutLabel(): string {
  return isMacPlatform() ? '⌘K' : 'Ctrl+K'
}

export function pinsShortcutLabel(): string {
  return isMacPlatform() ? '⌥1–9' : 'Alt+1–9'
}
