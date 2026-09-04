import { describe, expect, it } from 'vitest'
import { formatStoreSize } from '../localStore'

describe('formatStoreSize', () => {
  it('uses not created yet for missing or empty sizes', () => {
    expect(formatStoreSize(null)).toBe('not created yet')
    expect(formatStoreSize(undefined)).toBe('not created yet')
    expect(formatStoreSize(0)).toBe('not created yet')
    expect(formatStoreSize(-1)).toBe('not created yet')
  })

  it('formats a human-readable local store size', () => {
    expect(formatStoreSize(500)).toBe('500 B')
    expect(formatStoreSize(2048)).toBe('2.0 KB')
    expect(formatStoreSize(13_002_342)).toBe('12.4 MB')
  })
})