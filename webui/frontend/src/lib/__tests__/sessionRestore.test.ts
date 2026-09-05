import { describe, expect, it } from 'vitest'
import {
  MISSING_SESSION_TEXT,
  RESTORED_SESSION_TEXT,
  hasRestorableTurns,
  isRestoreStatusText,
  missingSessionNotice,
  restoreKindForAgent,
  restoredSessionNotice,
  switchedSessionNotice,
  withRestoredSession,
} from '../sessionRestore'

describe('restoreKindForAgent (REQ-161)', () => {
  it('classifies CLI, API, remote, and team ids', () => {
    expect(restoreKindForAgent('cli_agent')).toBe('cli')
    expect(restoreKindForAgent('api_agent')).toBe('api')
    expect(restoreKindForAgent('grok_agent')).toBe('cli')
    expect(restoreKindForAgent('agy_agent')).toBe('cli')
    expect(restoreKindForAgent('opencode_agent')).toBe('cli')
    expect(restoreKindForAgent('pi_agent')).toBe('cli')
    expect(restoreKindForAgent('codey')).toBe('api')
    expect(restoreKindForAgent('jeeves')).toBe('api')
    expect(restoreKindForAgent('remote:omb')).toBe('remote')
    expect(restoreKindForAgent('remote-omb')).toBe('remote')
    expect(restoreKindForAgent('team-demo-team')).toBe('team')
    expect(restoreKindForAgent('team:demo-team')).toBe('team')
  })
})

describe('withRestoredSession', () => {
  it('does not fake a line on an empty or status-only thread', () => {
    expect(withRestoredSession([], 'api')).toEqual([])
    expect(withRestoredSession([], 'cli')).toEqual([])
    expect(withRestoredSession([], 'remote')).toEqual([])
    expect(withRestoredSession([], 'team')).toEqual([])
    const statusOnly = [{ role: 'status', content: 'CLI: antigravity → grok' }]
    expect(hasRestorableTurns(statusOnly)).toBe(false)
    expect(withRestoredSession(statusOnly, 'cli')).toEqual(statusOnly)
    expect(restoredSessionNotice(statusOnly, 'cli')).toBeNull()
  })

  it('prepends kind-aware chrome when prior turns exist', () => {
    const prior = [
      { role: 'user', content: 'hi' },
      { role: 'assistant', content: 'hello' },
    ]
    expect(withRestoredSession(prior, 'api')[0]).toEqual({
      role: 'status',
      content: RESTORED_SESSION_TEXT.api,
    })
    expect(withRestoredSession(prior, 'cli')[0].content).toBe('Resumed CLI session')
    expect(withRestoredSession(prior, 'remote')[0].content).toBe('Reconnected remote')
    expect(withRestoredSession(prior, 'team')[0].content).toBe('Restored session')
    expect(withRestoredSession(prior, 'api')).toHaveLength(3)
  })

  it('does not duplicate an existing resume/restore status', () => {
    const already = [
      { role: 'status', content: 'Resumed grok session.' },
      { role: 'user', content: 'hi' },
    ]
    expect(withRestoredSession(already, 'cli')).toEqual(already)
    expect(isRestoreStatusText('Started a new grok session.')).toBe(false)
    expect(isRestoreStatusText('Switched to session Notes')).toBe(true)
    expect(switchedSessionNotice('Notes')).toBe('Switched to session Notes')
    expect(switchedSessionNotice('')).toBe('Switched to session')
  })
})

describe('missingSessionNotice (#794)', () => {
  it('is honest and never claims restore', () => {
    expect(missingSessionNotice('sess-gone')).toBe('Stored session sess-gone is gone')
    expect(missingSessionNotice('')).toBe(MISSING_SESSION_TEXT)
    expect(isRestoreStatusText('Stored session sess-gone is gone')).toBe(true)
    expect(isRestoreStatusText('Stored session is gone')).toBe(true)
  })
})
