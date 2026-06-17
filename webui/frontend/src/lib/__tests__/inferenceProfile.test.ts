import { describe, it, expect } from 'vitest'
import { resolve, rank, splitCandidate } from '../inferenceProfile'

const CANDIDATES = {
  smart: { intelligence: 0.95, speed: 0.4, cost: 0.3 },
  fast_cheap: { intelligence: 0.55, speed: 0.95, cost: 0.95 },
  allrounder: { intelligence: 0.6, speed: 0.6, cost: 0.6 },
}

describe('inferenceProfile.resolve (distance-from-ideal)', () => {
  it('single-axis target ignores other axes', () => {
    expect(resolve({ intelligence: 1.0 }, CANDIDATES)).toBe('smart')
  })

  it('fast+cheap target', () => {
    expect(resolve({ speed: 1.0, cost: 1.0 }, CANDIDATES)).toBe('fast_cheap')
  })

  it('balanced picks the all-rounder, not highest-aggregate', () => {
    expect(resolve({ intelligence: 0.6, speed: 0.6, cost: 0.6 }, CANDIDATES)).toBe('allrounder')
  })

  it('ranks best-first and tie-breaks by name', () => {
    const flat = { b: { intelligence: 0.5 }, a: { intelligence: 0.5 } }
    expect(rank({ intelligence: 0.5 }, flat).map((r) => r.name)).toEqual(['a', 'b'])
  })

  it('resolve returns null with no candidates', () => {
    expect(resolve({ intelligence: 1 }, {})).toBeNull()
  })
})

describe('splitCandidate', () => {
  it('splits cli@model and bare cli', () => {
    expect(splitCandidate('gemini@pro')).toEqual(['gemini', 'pro'])
    expect(splitCandidate('grok')).toEqual(['grok', null])
  })
})

import { buildCandidates } from '../../components/InferenceProfilePanel'

describe('buildCandidates', () => {
  it('adds cli@model candidates matched to their CLI by name prefix', () => {
    const cli = { gemini: { intelligence: 0.6 }, grok: { intelligence: 0.9 } }
    const models = { 'gemini-3-pro-preview': { intelligence: 0.95 } }
    const c = buildCandidates(cli, models)
    expect(Object.keys(c).sort()).toEqual(['gemini', 'gemini@gemini-3-pro-preview', 'grok'])
  })
})
