import { afterEach, describe, expect, it } from 'vitest'
import {
  SPA_HELLO_EVENT,
  getExpectedSpaVersion,
  publishExpectedSpaVersion,
  resetExpectedSpaVersion,
} from '../spaHello'

describe('spaHello bus', () => {
  afterEach(() => {
    resetExpectedSpaVersion()
  })

  it('starts empty so first paint cannot show a false update', () => {
    expect(getExpectedSpaVersion()).toBeNull()
  })

  it('publishes a trimmed version and can reset', () => {
    const seen: Array<string | null> = []
    const onHello = (event: Event) => {
      seen.push((event as CustomEvent<string | null>).detail)
    }
    window.addEventListener(SPA_HELLO_EVENT, onHello)
    publishExpectedSpaVersion('  0.5.4  ')
    expect(getExpectedSpaVersion()).toBe('0.5.4')
    resetExpectedSpaVersion()
    expect(getExpectedSpaVersion()).toBeNull()
    window.removeEventListener(SPA_HELLO_EVENT, onHello)
    expect(seen).toEqual(['0.5.4'])
  })
})
