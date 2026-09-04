/**
 * Narrow vs wide rail chrome. Matches Tailwind / DaisyUI `lg` (1024px),
 * the existing Grok-Bot drawer split (`lg:static` / `lg:hidden`).
 */

export const NARROW_RAIL_MAX_PX = 1023
export const NARROW_RAIL_MEDIA = `(max-width: ${NARROW_RAIL_MAX_PX}px)`

export function isNarrowViewport(): boolean {
  if (typeof window === 'undefined') return false
  try {
    if (typeof window.matchMedia === 'function') {
      return window.matchMedia(NARROW_RAIL_MEDIA).matches
    }
  } catch {
    /* matchMedia unavailable */
  }
  return window.innerWidth <= NARROW_RAIL_MAX_PX
}

export function subscribeNarrowViewport(onChange: (narrow: boolean) => void): () => void {
  if (typeof window === 'undefined') return () => undefined
  try {
    if (typeof window.matchMedia === 'function') {
      const mq = window.matchMedia(NARROW_RAIL_MEDIA)
      const handler = () => onChange(mq.matches)
      mq.addEventListener('change', handler)
      return () => mq.removeEventListener('change', handler)
    }
  } catch {
    /* fall through to resize */
  }
  const handler = () => onChange(isNarrowViewport())
  window.addEventListener('resize', handler)
  return () => window.removeEventListener('resize', handler)
}
