/**
 * First-concealment swipe hint. Dismissed state persists best-effort,
 * same pattern as the editable rail hostname.
 */

export const SWIPE_HINT_STORAGE_KEY = 'swarm_swipe_hint_dismissed'

export function isSwipeHintDismissed(): boolean {
  try {
    return localStorage.getItem(SWIPE_HINT_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function dismissSwipeHint(): void {
  try {
    localStorage.setItem(SWIPE_HINT_STORAGE_KEY, '1')
  } catch {
    /* persistence is best-effort */
  }
}
