import { describe, expect, it } from 'vitest'
import {
  filterCliSessions,
  formatActivityAge,
  looksLikeSessionId,
  sanitizeCliSessionId,
  type CliProviderSession,
} from '../cliSessions'

function row(id: string, title: string, snippet = ''): CliProviderSession {
  return {
    id,
    title,
    snippet,
    updated_at: '2026-09-05T12:00:00Z',
    source: 'swarm',
  }
}

describe('sanitizeCliSessionId', () => {
  it('accepts storeable ids and rejects secrets / junk', () => {
    expect(sanitizeCliSessionId('sid-ok_1')).toBe('sid-ok_1')
    expect(sanitizeCliSessionId('ses_abc')).toBe('ses_abc')
    expect(sanitizeCliSessionId('sk-live-secret-key')).toBeNull()
    expect(sanitizeCliSessionId('has space')).toBeNull()
    expect(sanitizeCliSessionId('a/b')).toBeNull()
    expect(sanitizeCliSessionId('')).toBeNull()
  })
})

describe('looksLikeSessionId', () => {
  it('mirrors sanitize for paste-id', () => {
    expect(looksLikeSessionId('uuid-like-session')).toBe(true)
    expect(looksLikeSessionId('sk-abc')).toBe(false)
  })
})

describe('formatActivityAge', () => {
  const now = Date.parse('2026-09-05T18:00:00')

  it('uses relative stamps for recent activity', () => {
    expect(formatActivityAge(now - 30_000, now)).toBe('just now')
    expect(formatActivityAge(now - 2 * 60_000, now)).toBe('2m ago')
    expect(formatActivityAge(now - 3 * 60 * 60_000, now)).toBe('3h ago')
    const yesterday = new Date(now)
    yesterday.setDate(yesterday.getDate() - 1)
    yesterday.setHours(15, 0, 0, 0)
    expect(formatActivityAge(yesterday.getTime(), now)).toBe('Yesterday')
  })

  it('returns empty for missing or invalid stamps', () => {
    expect(formatActivityAge('', now)).toBe('')
    expect(formatActivityAge('not-a-date', now)).toBe('')
  })
})

describe('filterCliSessions', () => {
  const sessions = [
    row('sid-1', 'First', 'hello'),
    row('sid-2', 'Second', 'again'),
  ]

  it('filters by title, snippet, or id', () => {
    expect(filterCliSessions(sessions, 'second').map((s) => s.id)).toEqual(['sid-2'])
    expect(filterCliSessions(sessions, 'hello').map((s) => s.id)).toEqual(['sid-1'])
    expect(filterCliSessions(sessions, 'sid-2').map((s) => s.id)).toEqual(['sid-2'])
    expect(filterCliSessions(sessions, '')).toHaveLength(2)
  })
})
