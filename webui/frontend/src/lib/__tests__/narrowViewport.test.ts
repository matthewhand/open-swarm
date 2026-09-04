import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  NARROW_RAIL_MAX_PX,
  NARROW_RAIL_MEDIA,
  isNarrowViewport,
  subscribeNarrowViewport,
} from '../narrowViewport'

type ChangeListener = EventListener

function stubMatchMedia(matches: boolean, listeners: Set<ChangeListener> = new Set()) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addEventListener: (_event: string, fn: ChangeListener) => {
      listeners.add(fn)
    },
    removeEventListener: (_event: string, fn: ChangeListener) => {
      listeners.delete(fn)
    },
    addListener: (fn: ChangeListener) => {
      listeners.add(fn)
    },
    removeListener: (fn: ChangeListener) => {
      listeners.delete(fn)
    },
    dispatchEvent: () => false,
  }))
}

describe('narrowViewport', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('treats max-width 1023px as narrow (Tailwind lg split)', () => {
    expect(NARROW_RAIL_MAX_PX).toBe(1023)
    expect(NARROW_RAIL_MEDIA).toBe('(max-width: 1023px)')
    stubMatchMedia(true)
    expect(isNarrowViewport()).toBe(true)
    stubMatchMedia(false)
    expect(isNarrowViewport()).toBe(false)
  })

  it('notifies subscribers when the media query changes', () => {
    const listeners = new Set<ChangeListener>()
    stubMatchMedia(true, listeners)
    const onChange = vi.fn()
    const unsubscribe = subscribeNarrowViewport(onChange)
    expect(listeners.size).toBe(1)
    listeners.forEach((fn) => fn(new Event('change')))
    expect(onChange).toHaveBeenCalled()
    unsubscribe()
    expect(listeners.size).toBe(0)
  })
})
