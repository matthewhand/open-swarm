import { describe, it, expect } from 'vitest'
import {
  buildSkillParams,
  buildSkillRequest,
  findSkillRefs,
  parseComposerSkillNames,
  skillLookupError,
  splitSkillRefs,
} from '../skills'

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

describe('REQ-212 skill attach helpers', () => {
  it('parses one or more /skill names from composer text', () => {
    expect(parseComposerSkillNames('/skill conventional-commit write it')).toEqual([
      'conventional-commit',
    ])
    expect(
      parseComposerSkillNames('/skill conventional-commit /skill writing-changelog more'),
    ).toEqual(['conventional-commit', 'writing-changelog'])
  })

  it('builds skill and skills params', () => {
    expect(buildSkillParams([])).toEqual({})
    expect(buildSkillParams(['conventional-commit'])).toEqual({
      skill: 'conventional-commit',
      skills: ['conventional-commit'],
    })
    expect(buildSkillParams(['a', 'b'])).toEqual({ skills: ['a', 'b'] })
  })

  it('finds slash, path, and skill: refs but skips fenced code', () => {
    const text = [
      'Use /skill conventional-commit then skills/writing-changelog/SKILL.md',
      '',
      '```',
      'skills/reviewing-code/SKILL.md',
      '```',
      '',
      'Also skill:counting-lines',
    ].join('\n')
    const refs = findSkillRefs(text)
    expect(refs.map((ref) => ref.name)).toEqual([
      'conventional-commit',
      'writing-changelog',
      'counting-lines',
    ])
    expect(refs[1].kind).toBe('path')
  })

  it('splits text around skill chips', () => {
    const segments = splitSkillRefs('see skills/haiku/SKILL.md please')
    expect(segments).toEqual([
      { type: 'text', text: 'see ' },
      {
        type: 'skill',
        ref: {
          name: 'haiku',
          raw: 'skills/haiku/SKILL.md',
          kind: 'path',
          start: 4,
          end: 25,
        },
      },
      { type: 'text', text: ' please' },
    ])
  })

  it('honest missing copy names SKILL.md', () => {
    expect(skillLookupError('nope')).toContain('nope')
    expect(skillLookupError('nope')).toContain('SKILL.md')
  })
})
