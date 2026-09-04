import { afterEach, describe, expect, it } from 'vitest'
import {
  BUMP_COMPLETED_KEY,
  HOSTNAME_OVERRIDE_KEY,
  RETENTION_MODE_KEY,
  isRetentionMode,
  loadBumpCompleted,
  loadHostnameOverride,
  loadRetentionMode,
  saveBumpCompleted,
  saveHostnameOverride,
  saveRetentionMode,
} from '../settingsPrefs'

describe('settingsPrefs', () => {
  afterEach(() => {
    localStorage.removeItem(HOSTNAME_OVERRIDE_KEY)
    localStorage.removeItem(RETENTION_MODE_KEY)
    localStorage.removeItem(BUMP_COMPLETED_KEY)
  })

  it('treats only Count/Disk/Archive/Trash ids as retention modes', () => {
    expect(isRetentionMode('count')).toBe(true)
    expect(isRetentionMode('trash')).toBe(true)
    expect(isRetentionMode('btn-group')).toBe(false)
    expect(isRetentionMode('')).toBe(false)
  })

  it('persists and clears a hostname override', () => {
    expect(loadHostnameOverride()).toBe('')
    saveHostnameOverride('  swarm.example.com  ')
    expect(localStorage.getItem(HOSTNAME_OVERRIDE_KEY)).toBe('swarm.example.com')
    expect(loadHostnameOverride()).toBe('swarm.example.com')
    saveHostnameOverride('   ')
    expect(localStorage.getItem(HOSTNAME_OVERRIDE_KEY)).toBeNull()
  })

  it('defaults retention to count and restores a stored mode', () => {
    expect(loadRetentionMode()).toBe('count')
    saveRetentionMode('archive')
    expect(localStorage.getItem(RETENTION_MODE_KEY)).toBe('archive')
    expect(loadRetentionMode()).toBe('archive')
    localStorage.setItem(RETENTION_MODE_KEY, 'not-a-mode')
    expect(loadRetentionMode()).toBe('count')
  })

  it('defaults bump-completed on and persists off', () => {
    expect(loadBumpCompleted()).toBe(true)
    expect(saveBumpCompleted(false)).toBe(false)
    expect(localStorage.getItem(BUMP_COMPLETED_KEY)).toBe('0')
    expect(loadBumpCompleted()).toBe(false)
    saveBumpCompleted(true)
    expect(loadBumpCompleted()).toBe(true)
  })
})
