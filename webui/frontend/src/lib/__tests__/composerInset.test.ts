import { describe, expect, it } from 'vitest'
import {
  COMPOSER_INSET_VAR,
  COMPOSER_PIN_SLACK_PX,
  composerInsetCustomProperty,
  isPinnedToTranscriptBottom,
  measureComposerDockInset,
  scrollTranscriptToBottom,
} from '../composerInset'

describe('composerInset helpers (#743)', () => {
  it('measures dock height with ceil and ignores missing nodes', () => {
    expect(measureComposerDockInset(null)).toBe(0)

    const dock = document.createElement('div')
    dock.getBoundingClientRect = () =>
      ({
        x: 0,
        y: 0,
        top: 0,
        left: 0,
        right: 320,
        bottom: 87.4,
        width: 320,
        height: 87.4,
        toJSON: () => ({}),
      }) as DOMRect

    expect(measureComposerDockInset(dock)).toBe(88)
  })

  it('falls back to offsetHeight when getBoundingClientRect height is 0', () => {
    const dock = document.createElement('div')
    Object.defineProperty(dock, 'offsetHeight', { value: 64, configurable: true })
    dock.getBoundingClientRect = () =>
      ({
        x: 0,
        y: 0,
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: 0,
        height: 0,
        toJSON: () => ({}),
      }) as DOMRect

    expect(measureComposerDockInset(dock)).toBe(64)
  })

  it('exposes the live inset as a CSS custom property', () => {
    expect(composerInsetCustomProperty(96)).toEqual({
      [COMPOSER_INSET_VAR]: '96px',
    })
    expect(composerInsetCustomProperty(-4)).toEqual({
      [COMPOSER_INSET_VAR]: '0px',
    })
  })

  it('treats the user as pinned when remaining scroll is within inset slack', () => {
    const nearBottom = { scrollHeight: 2000, scrollTop: 1920, clientHeight: 80 }
    const scrolledUp = { scrollHeight: 2000, scrollTop: 1600, clientHeight: 80 }
    expect(isPinnedToTranscriptBottom(nearBottom, 96)).toBe(true)
    expect(isPinnedToTranscriptBottom(scrolledUp, 96)).toBe(false)
    expect(COMPOSER_PIN_SLACK_PX).toBe(48)
  })

  it('scrolls the transcript box to its end', () => {
    const box = document.createElement('div')
    Object.defineProperty(box, 'scrollHeight', { value: 2400, configurable: true })
    box.scrollTop = 12
    scrollTranscriptToBottom(box)
    expect(box.scrollTop).toBe(2400)
  })
})
