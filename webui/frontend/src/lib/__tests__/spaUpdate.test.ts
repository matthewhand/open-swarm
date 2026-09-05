import { describe, expect, it } from 'vitest'
import {
  isNewerVersion,
  normalizeVersion,
  resolveUpdateChrome,
  versionsEqual,
} from '../spaUpdate'

describe('spaUpdate version helpers', () => {
  it('strips a leading v and compares equality', () => {
    expect(normalizeVersion(' v0.5.4 ')).toBe('0.5.4')
    expect(versionsEqual('v0.5.4', '0.5.4')).toBe(true)
    expect(versionsEqual('0.5.4', '0.5.5')).toBe(false)
  })

  it('detects a strictly newer dotted release', () => {
    expect(isNewerVersion('0.5.5', '0.5.4')).toBe(true)
    expect(isNewerVersion('v0.6.0', '0.5.9')).toBe(true)
    expect(isNewerVersion('0.5.4', '0.5.4')).toBe(false)
    expect(isNewerVersion('0.5.3', '0.5.4')).toBe(false)
    expect(isNewerVersion('not-a-version', '0.5.4')).toBe(false)
  })
})

describe('resolveUpdateChrome (REQ-78 XOR + priority)', () => {
  it('match → idle ⓘ (first paint: no hello, no GitHub)', () => {
    expect(
      resolveUpdateChrome({
        bakedVersion: '0.5.4',
        backendVersion: null,
        githubLatest: null,
      }),
    ).toEqual({ kind: 'idle', alsoUpstream: false })
    expect(
      resolveUpdateChrome({
        bakedVersion: '0.5.4',
        backendVersion: 'v0.5.4',
        githubLatest: '0.5.4',
      }),
    ).toEqual({ kind: 'idle', alsoUpstream: false })
  })

  it('SPA mismatch only → colour A (local)', () => {
    expect(
      resolveUpdateChrome({
        bakedVersion: '0.5.3',
        backendVersion: '0.5.4',
        githubLatest: null,
      }),
    ).toEqual({ kind: 'local', alsoUpstream: false })
  })

  it('GitHub newer only → colour B (upstream)', () => {
    expect(
      resolveUpdateChrome({
        bakedVersion: '0.5.4',
        backendVersion: '0.5.4',
        githubLatest: '0.5.5',
      }),
    ).toEqual({ kind: 'upstream', alsoUpstream: false })
  })

  it('API fail / missing GitHub → no B', () => {
    expect(
      resolveUpdateChrome({
        bakedVersion: '0.5.4',
        backendVersion: '0.5.4',
        githubLatest: null,
      }),
    ).toEqual({ kind: 'idle', alsoUpstream: false })
  })

  it('both → local A wins and notes upstream in alsoUpstream', () => {
    expect(
      resolveUpdateChrome({
        bakedVersion: '0.5.3',
        backendVersion: '0.5.4',
        githubLatest: '0.5.5',
      }),
    ).toEqual({ kind: 'local', alsoUpstream: true })
  })
})
