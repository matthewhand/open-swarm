import { describe, it, expect } from 'vitest'
import {
  resolve,
  rank,
  splitCandidate,
  buildTraitsConfig,
  candidatesFromEdits,
  cliForModel
} from '../inferenceProfile'
import { buildCandidates } from '../../components/InferenceProfilePanel'

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

  it('missing candidate throws', () => {
    expect(() => resolve({ intelligence: 1.0 }, {})).toThrow(/No candidates/)
  })
})

describe('inferenceProfile.rank', () => {
  it('returns all candidates sorted by distance', () => {
    const r = rank({ intelligence: 1.0, speed: 1.0 }, CANDIDATES)
    expect(r.map((x) => x.name)).toEqual(['allrounder', 'fast_cheap', 'smart'])
  })
})

describe('splitCandidate', () => {
  it('parses model and optional fallback', () => {
    expect(splitCandidate('gpt-4')).toEqual(['gpt-4', undefined])
    expect(splitCandidate('claude-3-5|gpt-4o')).toEqual(['claude-3-5', 'gpt-4o'])
  })
})

describe('buildCandidates', () => {
  it('combines defaults and edits, dropping nulls', () => {
    const edits = {
      'gpt-4': { cost: 0.1 },
      'claude-3': null, // dropped
    }
    const defaults = {
      'gpt-4': { intelligence: 0.9 },
      'claude-3': { intelligence: 0.8 },
    }
    const combined = buildCandidates(defaults as any, edits as any)
    expect(combined).toEqual({ 'gpt-4': { intelligence: 0.9, cost: 0.1 } })
  })
})

describe('buildTraitsConfig', () => {
  it('emits cli traits + per-model models block', () => {
    const cfg = buildTraitsConfig(
      { intelligence: 0.9, speed: 0.5 },
      { 'gpt-4o': { intelligence: 0.9 } }
    )
    expect(cfg.traits).toEqual({ intelligence: 0.9, speed: 0.5 })
    expect(cfg.models['gpt-4o']).toEqual({ intelligence: 0.9 })
  })
})

describe('candidatesFromEdits', () => {
  it('flattens non-null edits to traits', () => {
    expect(candidatesFromEdits({ x: { speed: 1 }, y: null })).toEqual({
      x: { speed: 1 },
    })
  })
})

describe('buildCandidates prefix matching (bug hunt)', () => {
  it('does not overwrite exact keys with prefix matches', () => {
    const defaults = {
      'claude-3-5-sonnet-20241022': { intelligence: 0.9 },
      'claude-3-5-sonnet-latest': { intelligence: 0.95 },
    }
    const edits = {
      'claude-3-5-sonnet-latest': { cost: 0.2 },
    }
    // "claude-3-5-sonnet" is a prefix of both, but if the UI edited the exact key,
    // it shouldn't splatter over the non-edited exact key.
    const combined = buildCandidates(defaults as any, edits as any)
    expect(combined['claude-3-5-sonnet-20241022']).toEqual({ intelligence: 0.9 })
    expect(combined['claude-3-5-sonnet-latest']).toEqual({ intelligence: 0.95, cost: 0.2 })
  })
})

describe('cliForModel', () => {
  it('picks the longest CLI matching at a hyphen boundary', () => {
    expect(cliForModel('claude-opus-4-8', ['c', 'claude'])).toBe('claude')
    expect(cliForModel('gpt-4o', ['gpt', 'claude'])).toBe('gpt')
  })
  it('falls back to "default" if no match', () => {
    expect(cliForModel('unknown-model', ['gpt', 'claude'])).toBe('default')
  })
})
