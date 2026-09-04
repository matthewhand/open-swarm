import { useEffect, useRef } from 'react'

/** Finger must begin at or inside this many CSS pixels from the left edge. */
export const LEFT_EDGE_PX = 24
/** Horizontal travel required before the rail reopens. */
export const MIN_SWIPE_DX = 48

export function isLeftEdgeRestoreSwipe(
  startX: number,
  startY: number,
  endX: number,
  endY: number,
): boolean {
  if (startX > LEFT_EDGE_PX) return false
  const dx = endX - startX
  const dy = Math.abs(endY - startY)
  return dx >= MIN_SWIPE_DX && dx >= dy
}

/**
 * Native touch only — no extra gesture library. Enabled while the rail is
 * tucked on a narrow viewport so a left-edge swipe restores the list.
 */
export function useLeftEdgeSwipe(enabled: boolean, onSwipe: () => void): void {
  const onSwipeRef = useRef(onSwipe)
  onSwipeRef.current = onSwipe

  useEffect(() => {
    if (!enabled) return
    let startX = 0
    let startY = 0
    let tracking = false

    const onStart = (event: TouchEvent) => {
      const touch = event.touches[0]
      if (!touch) return
      if (touch.clientX <= LEFT_EDGE_PX) {
        tracking = true
        startX = touch.clientX
        startY = touch.clientY
      }
    }

    const onMove = (event: TouchEvent) => {
      if (!tracking) return
      const touch = event.touches[0]
      if (!touch) return
      if (isLeftEdgeRestoreSwipe(startX, startY, touch.clientX, touch.clientY)) {
        tracking = false
        onSwipeRef.current()
      }
    }

    const onEnd = () => {
      tracking = false
    }

    window.addEventListener('touchstart', onStart, { passive: true })
    window.addEventListener('touchmove', onMove, { passive: true })
    window.addEventListener('touchend', onEnd)
    window.addEventListener('touchcancel', onEnd)
    return () => {
      window.removeEventListener('touchstart', onStart)
      window.removeEventListener('touchmove', onMove)
      window.removeEventListener('touchend', onEnd)
      window.removeEventListener('touchcancel', onEnd)
    }
  }, [enabled])
}
