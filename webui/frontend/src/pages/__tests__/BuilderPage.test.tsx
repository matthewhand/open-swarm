import { describe, it, expect } from 'vitest'
import { bestOfNFlags, NATIVE_CONSENSUS } from '../BuilderPage'

describe('bestOfNFlags', () => {
  it('builds grok best-of-n flags with the count substituted', () => {
    expect(bestOfNFlags('grok', 3)).toEqual(['--best-of-n', '3'])
  })

  it('clamps N to a minimum of 2', () => {
    expect(bestOfNFlags('grok', 1)).toEqual(['--best-of-n', '2'])
  })

  it('returns null for a CLI with no built-in consensus mode', () => {
    expect(bestOfNFlags('claude', 3)).toBeNull()
  })

  it('mirrors the backend native-consensus map shape', () => {
    expect(NATIVE_CONSENSUS.grok).toEqual(['--best-of-n', '{n}'])
  })
})
