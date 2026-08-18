import { describe, it, expect } from 'vitest'
import {
  MAX_AUTO_RECONNECT_ATTEMPTS,
  reconnectBackoffMs,
  shouldAutoReconnect,
  WS_AUTH_REQUIRED_CODE,
} from '../chatReconnect'

describe('reconnectBackoffMs', () => {
  it('doubles from 1s and caps at 16s', () => {
    expect(reconnectBackoffMs(0)).toBe(1000)
    expect(reconnectBackoffMs(1)).toBe(2000)
    expect(reconnectBackoffMs(2)).toBe(4000)
    expect(reconnectBackoffMs(10)).toBe(16_000)
  })
})

describe('shouldAutoReconnect', () => {
  it('skips intentional closes and auth gate 4401', () => {
    expect(shouldAutoReconnect(1006, true, 0)).toBe(false)
    expect(shouldAutoReconnect(WS_AUTH_REQUIRED_CODE, false, 0)).toBe(false)
  })

  it('allows unexpected closes until max attempts', () => {
    expect(shouldAutoReconnect(1006, false, 0)).toBe(true)
    expect(shouldAutoReconnect(1000, false, 3)).toBe(true)
    expect(
      shouldAutoReconnect(1006, false, MAX_AUTO_RECONNECT_ATTEMPTS),
    ).toBe(false)
  })
})
