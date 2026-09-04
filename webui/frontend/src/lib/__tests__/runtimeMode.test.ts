import { afterEach, describe, expect, it } from 'vitest'
import {
  RUNTIME_BANNER_STORAGE_KEY,
  clearDismissedRuntimeMode,
  isRuntimeBannerDismissed,
  loadDismissedRuntimeMode,
  parseRuntimeBanner,
  saveDismissedRuntimeMode,
} from '../runtimeMode'

describe('parseRuntimeBanner', () => {
  it('keeps warning tones for bare-metal and sandbox-home', () => {
    for (const mode of ['bare-metal', 'sandbox-home'] as const) {
      const parsed = parseRuntimeBanner({
        mode,
        known: true,
        tone: 'warning',
        title: 'Warn',
        message: 'This instance is bare metal, or a developer sandbox with full $HOME access',
      })
      expect(parsed.mode).toBe(mode)
      expect(parsed.tone).toBe('warning')
      expect(parsed.known).toBe(true)
    }
  })

  it('keeps isolated as info (green/info), not unknown', () => {
    const parsed = parseRuntimeBanner({
      mode: 'sandbox-isolated',
      known: true,
      tone: 'info',
      title: 'Sandboxed',
      message: 'You appear to be in a sandbox env',
    })
    expect(parsed.tone).toBe('info')
    expect(parsed.mode).toBe('sandbox-isolated')
  })

  it('treats missing or junk payload as unknown — never fake green', () => {
    expect(parseRuntimeBanner(null).tone).toBe('unknown')
    expect(parseRuntimeBanner({ data: [] }).tone).toBe('unknown')
    expect(parseRuntimeBanner({ mode: 'unknown', tone: 'info', title: 'x', message: 'y' }).tone).toBe(
      'unknown',
    )
    expect(parseRuntimeBanner({ mode: '/home/ubuntu', tone: 'info', title: 'x', message: 'y' }).tone).toBe(
      'unknown',
    )
  })
})

describe('runtime banner dismiss persistence', () => {
  afterEach(() => {
    clearDismissedRuntimeMode()
  })

  it('persists the dismissed mode and re-shows when the mode changes', () => {
    expect(isRuntimeBannerDismissed('bare-metal')).toBe(false)
    saveDismissedRuntimeMode('bare-metal')
    expect(loadDismissedRuntimeMode()).toBe('bare-metal')
    expect(localStorage.getItem(RUNTIME_BANNER_STORAGE_KEY)).toBe('bare-metal')
    expect(isRuntimeBannerDismissed('bare-metal')).toBe(true)
    expect(isRuntimeBannerDismissed('sandbox-isolated')).toBe(false)
  })
})
