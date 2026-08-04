import { describe, it, expect } from 'vitest'
import { buildSkillRequest } from '../skills'

describe('buildSkillRequest', () => {
  it('returns null when no skill selected', () => {
    expect(buildSkillRequest(null)).toBeNull()
  })
  it('builds a cli_agent request with skill param', () => {
    expect(buildSkillRequest('conventional-commit')).toEqual({
      model: 'cli_agent',
      params: { skill: 'conventional-commit' },
    })
  })
})
