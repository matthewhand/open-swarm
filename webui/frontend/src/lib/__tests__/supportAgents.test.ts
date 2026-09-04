import { describe, expect, it } from 'vitest'
import {
  findSupportAgent,
  isSupportAgent,
  roleTone,
  sortSupportFirst,
} from '../supportAgents'

const agents = [
  { id: 'codey', role: null },
  { id: 'skeptic', role: 'skeptic' },
  { id: 'gate', role: 'gate' },
  { id: 'support', role: 'support' },
] as const

describe('supportAgents', () => {
  it('sorts support, then gate, then skeptic', () => {
    expect(sortSupportFirst([...agents]).map((a) => a.id)).toEqual([
      'support',
      'gate',
      'skeptic',
      'codey',
    ])
  })

  it('treats role=support as the Support agent', () => {
    expect(isSupportAgent({ id: 'helper', role: 'support' })).toBe(true)
    expect(findSupportAgent([...agents])?.id).toBe('support')
  })

  it('maps special roles to distinct tones', () => {
    expect(roleTone({ id: 'support', role: 'support' })).toBe('support')
    expect(roleTone({ id: 'gate', role: 'gate' })).toBe('gate')
    expect(roleTone({ id: 'skeptic', role: 'skeptic' })).toBe('skeptic')
    expect(roleTone({ id: 'codey', role: null })).toBe('')
  })
})
