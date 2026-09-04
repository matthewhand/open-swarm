import { afterEach, describe, expect, it } from 'vitest'
import {
  SWIPE_HINT_STORAGE_KEY,
  dismissSwipeHint,
  isSwipeHintDismissed,
} from '../swipeHint'

describe('swipe hint persistence', () => {
  afterEach(() => {
    localStorage.removeItem(SWIPE_HINT_STORAGE_KEY)
  })

  it('defaults to not dismissed and persists dismiss best-effort', () => {
    expect(isSwipeHintDismissed()).toBe(false)
    dismissSwipeHint()
    expect(isSwipeHintDismissed()).toBe(true)
    expect(localStorage.getItem(SWIPE_HINT_STORAGE_KEY)).toBe('1')
  })
})
