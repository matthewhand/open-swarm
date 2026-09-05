import { describe, expect, it } from 'vitest'
import {
  formatRoutineHistoryTime,
  triggerSummary,
  defaultTrigger,
  ROUTINE_TRIGGER_GITHUB_PR_MERGED,
} from '../routines'

describe('triggerSummary', () => {
  it('summarizes a GitHub PR-merge trigger', () => {
    expect(
      triggerSummary({
        kind: ROUTINE_TRIGGER_GITHUB_PR_MERGED,
        owner_repo: 'owner/repo',
        event: 'merged',
        actor: 'anyone',
      }),
    ).toBe('When a PR merges in owner/repo…')
    expect(triggerSummary(defaultTrigger())).toBe('When a PR merges in a GitHub repo…')
  })
})

describe('formatRoutineHistoryTime', () => {
  const now = Date.parse('2026-09-05T21:34:00.000Z')

  it('uses Just now, N min ago, and Today at', () => {
    expect(formatRoutineHistoryTime(now - 12_000, now, 'UTC')).toBe('Just now')
    expect(formatRoutineHistoryTime(now - 32 * 60 * 1000, now, 'UTC')).toBe('32 min ago')
    expect(formatRoutineHistoryTime(Date.parse('2026-09-05T07:34:00.000Z'), now, 'UTC')).toBe(
      'Today at 7:34 AM',
    )
  })
})
