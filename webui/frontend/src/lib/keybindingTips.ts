/**
 * First-load keybinding tips. Dismissed state persists best-effort,
 * same pattern as the swipe hint and runtime banner.
 */

export const KEYBINDING_TIPS_STORAGE_KEY = 'swarm_keybinding_tips_dismissed'

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

export function isKeybindingTipsDismissed(): boolean {
  try {
    return localStorage.getItem(KEYBINDING_TIPS_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function dismissKeybindingTips(): void {
  try {
    localStorage.setItem(KEYBINDING_TIPS_STORAGE_KEY, '1')
  } catch {
    /* persistence is best-effort */
  }
}
