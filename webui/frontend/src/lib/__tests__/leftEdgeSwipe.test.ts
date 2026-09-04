import { describe, expect, it } from 'vitest'
import { LEFT_EDGE_PX, MIN_SWIPE_DX, isLeftEdgeRestoreSwipe } from '../leftEdgeSwipe'

describe('isLeftEdgeRestoreSwipe', () => {
  it('accepts a rightward swipe that starts on the left edge', () => {
    expect(isLeftEdgeRestoreSwipe(8, 200, 8 + MIN_SWIPE_DX, 204)).toBe(true)
  })

  it('rejects swipes that do not start on the left edge', () => {
    expect(isLeftEdgeRestoreSwipe(LEFT_EDGE_PX + 1, 200, 120, 200)).toBe(false)
  })

  it('rejects short or mostly-vertical gestures', () => {
    expect(isLeftEdgeRestoreSwipe(8, 200, 8 + MIN_SWIPE_DX - 1, 200)).toBe(false)
    expect(isLeftEdgeRestoreSwipe(8, 200, 40, 280)).toBe(false)
  })
})
