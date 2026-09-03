import { afterEach, describe, expect, it } from 'vitest'
import { HOSTNAME_STORAGE_KEY, defaultHostname, loadHostname, saveHostname } from '../hostname'
import {
  HOSTNAME_OVERRIDE_KEY,
  loadHostnameOverride,
  saveHostnameOverride,
} from '../settingsPrefs'

describe('hostname override', () => {
  afterEach(() => {
    localStorage.removeItem(HOSTNAME_STORAGE_KEY)
    localStorage.removeItem(HOSTNAME_OVERRIDE_KEY)
  })

  it('defaults to the browser hostname and persists an override', () => {
    expect(loadHostname()).toBe(defaultHostname())
    expect(saveHostname('lab-box')).toBe('lab-box')
    expect(loadHostname()).toBe('lab-box')
    expect(saveHostname('   ')).toBe(defaultHostname())
  })

  it('REQ-5c #322 / REQ-19 #320: rail hostname and settings override are independent keys', () => {
    expect(HOSTNAME_STORAGE_KEY).toBe('swarm_hostname')
    expect(HOSTNAME_OVERRIDE_KEY).toBe('swarm_hostname_override')
    expect(HOSTNAME_STORAGE_KEY).not.toBe(HOSTNAME_OVERRIDE_KEY)

    saveHostname('rail-box')
    saveHostnameOverride('settings.example.com')
    expect(loadHostname()).toBe('rail-box')
    expect(loadHostnameOverride()).toBe('settings.example.com')
    expect(localStorage.getItem(HOSTNAME_STORAGE_KEY)).toBe('rail-box')
    expect(localStorage.getItem(HOSTNAME_OVERRIDE_KEY)).toBe('settings.example.com')

    saveHostname('   ')
    expect(loadHostnameOverride()).toBe('settings.example.com')
  })
})
