import { afterEach, describe, expect, it } from 'vitest'
import { HOSTNAME_STORAGE_KEY, defaultHostname, loadHostname, saveHostname } from '../hostname'

describe('hostname override', () => {
  afterEach(() => {
    localStorage.removeItem(HOSTNAME_STORAGE_KEY)
  })

  it('defaults to the browser hostname and persists an override', () => {
    expect(loadHostname()).toBe(defaultHostname())
    expect(saveHostname('lab-box')).toBe('lab-box')
    expect(loadHostname()).toBe('lab-box')
    expect(saveHostname('   ')).toBe(defaultHostname())
  })
})
