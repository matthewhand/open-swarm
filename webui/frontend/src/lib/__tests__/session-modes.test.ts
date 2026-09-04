import { describe, expect, it } from 'vitest'
import { cycleSessionMode, normalizeSessionMode, sessionModeLabel } from '../session-modes'

describe('session modes', () => {
  it('cycles default → plan → auto-edit → default', () => {
    expect(cycleSessionMode('default')).toBe('plan')
    expect(cycleSessionMode('plan')).toBe('auto-edit')
    expect(cycleSessionMode('auto-edit')).toBe('default')
  })

  it('does not include always-approve', () => {
    const seen = new Set(
      ['default', 'plan', 'auto-edit'].map((m) => cycleSessionMode(m)),
    )
    expect([...seen].join(' ')).not.toMatch(/always|yolo|bypass/i)
  })

  it('normalizes acceptEdits to auto-edit', () => {
    expect(normalizeSessionMode('acceptEdits')).toBe('auto-edit')
    expect(sessionModeLabel('plan')).toBe('Plan')
  })
})
