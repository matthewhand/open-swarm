import { describe, it, expect, beforeEach } from 'vitest'
import {
  clampRailWidth,
  loadRailWidth,
  saveRailWidth,
  isAvatarOnlyWidth,
  MIN_RAIL_WIDTH,
  MAX_RAIL_WIDTH,
  DEFAULT_RAIL_WIDTH,
  AVATAR_ONLY_THRESHOLD,
  RAIL_WIDTH_STORAGE_KEY,
} from '../railResize'

describe('railResize (REQ-116)', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('clamps rail width within min and max boundaries', () => {
    expect(clampRailWidth(50)).toBe(MIN_RAIL_WIDTH)
    expect(clampRailWidth(100)).toBe(100)
    expect(clampRailWidth(500)).toBe(MAX_RAIL_WIDTH)
  })

  it('clamps rail width to viewport ceiling when specified', () => {
    // 45% of 600px is 270px, which is below MAX_RAIL_WIDTH (420px)
    expect(clampRailWidth(350, 600)).toBe(270)
  })

  it('loads default width when nothing is stored or value is invalid', () => {
    expect(loadRailWidth()).toBe(DEFAULT_RAIL_WIDTH)

    localStorage.setItem(RAIL_WIDTH_STORAGE_KEY, 'invalid')
    expect(loadRailWidth()).toBe(DEFAULT_RAIL_WIDTH)
  })

  it('persists and retrieves valid width from localStorage', () => {
    saveRailWidth(180)
    expect(localStorage.getItem(RAIL_WIDTH_STORAGE_KEY)).toBe('180')
    expect(loadRailWidth()).toBe(180)
  })

  it('identifies avatar-only width threshold', () => {
    expect(isAvatarOnlyWidth(MIN_RAIL_WIDTH)).toBe(true)
    expect(isAvatarOnlyWidth(AVATAR_ONLY_THRESHOLD)).toBe(true)
    expect(isAvatarOnlyWidth(AVATAR_ONLY_THRESHOLD + 1)).toBe(false)
    expect(isAvatarOnlyWidth(256)).toBe(false)
  })
})
