import { describe, it, expect } from 'vitest'
import { resolve, rank, splitCandidate, buildTraitsConfig, candidatesFromEdits, cliForModel } from '../inferenceProfile'
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

  it('resolve returns null when no scorable axis (empty or all-unknown)', () => {
    expect(resolve({}, CANDIDATES)).toBeNull()
    expect(resolve({ bogus: 1 }, CANDIDATES)).toBeNull()
  })
})

describe('splitCandidate', () => {
  it('splits cli@model and bare cli', () => {
    expect(splitCandidate('gemini@pro')).toEqual(['gemini', 'pro'])
    expect(splitCandidate('grok')).toEqual(['grok', null])
  })
})

describe('buildCandidates', () => {
  it('adds cli@model candidates matched to their CLI by name prefix', () => {
    const cli = { gemini: { intelligence: 0.6 }, grok: { intelligence: 0.9 } }
    const models = { 'gemini-3-pro-preview': { intelligence: 0.95 } }
    const c = buildCandidates(cli, models)
    expect(Object.keys(c).sort()).toEqual(['gemini', 'gemini@gemini-3-pro-preview', 'grok'])
  })
})

describe('buildTraitsConfig', () => {
  it('emits cli traits + per-model models block', () => {
    const cfg = buildTraitsConfig(
      { gemini: { intelligence: 0.6, speed: 0.9, cost: 0.9 } },
      [{ cli: 'gemini', model: 'gemini-3-pro', traits: { intelligence: 0.95, speed: 0.3, cost: 0.2 } }],
    )
    expect(cfg.cli_agents.gemini.traits).toEqual({ intelligence: 0.6, speed: 0.9, cost: 0.9 })
    expect(cfg.cli_agents.gemini.models?.['gemini-3-pro'].traits.intelligence).toBe(0.95)
  })
  it('skips blank model names', () => {
    const cfg = buildTraitsConfig({}, [{ cli: 'x', model: '', traits: {} }])
    expect(cfg.cli_agents).toEqual({})
  })
})

describe('candidatesFromEdits', () => {
  it('adds cli@model candidates from rows', () => {
    const c = candidatesFromEdits({ grok: { intelligence: 0.9 } }, [
      { cli: 'grok', model: 'fast', traits: { speed: 1 } },
    ])
    expect(Object.keys(c).sort()).toEqual(['grok', 'grok@fast'])
  })
})

describe('buildCandidates prefix matching (bug hunt)', () => {
  it('attributes a model to the longest matching CLI, not a short prefix', () => {
    const cli = { c: { intelligence: 0.5 }, claude: { intelligence: 0.9 } }
    const models = { 'claude-opus-4-8': { intelligence: 0.98 } }
    const out = buildCandidates(cli, models)
    expect(out['claude@claude-opus-4-8']).toBeDefined()
    expect(out['c@claude-opus-4-8']).toBeUndefined()
  })
})


describe('cliForModel', () => {
  it('picks the longest CLI matching at a hyphen boundary', () => {
    expect(cliForModel('claude-opus-4-8', ['c', 'claude'])).toBe('claude')
    expect(cliForModel('gemini-3-pro', ['gemini', 'gem'])).toBe('gemini')
    expect(cliForModel('grok', ['grok'])).toBe('grok') // exact
    expect(cliForModel('unknown-x', ['claude', 'gemini'])).toBeUndefined()
  })
})
