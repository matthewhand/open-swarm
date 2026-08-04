import { describe, it, expect } from 'vitest'
import { bestOfNFlags, buildAgentConfig, NATIVE_CONSENSUS } from '../BuilderPage'

const INFO = {
  catalog: { grok: { cmd: ['grok', '-p', '{prompt}'], parse: 'json:.text' } },
  native_consensus: { grok: ['--best-of-n', '{n}'] },
}

describe('bestOfNFlags', () => {
  it('builds grok flags with the count substituted, clamped to >=2', () => {
    expect(bestOfNFlags('grok', 3)).toEqual(['--best-of-n', '3'])
    expect(bestOfNFlags('grok', 1)).toEqual(['--best-of-n', '2'])
  })
  it('returns null for a CLI with no native mode', () => {
    expect(bestOfNFlags('claude', 3)).toBeNull()
  })
  it('mirrors the backend native-consensus map shape', () => {
    expect(NATIVE_CONSENSUS.grok).toEqual(['--best-of-n', '{n}'])
  })
})

describe('buildAgentConfig', () => {
  it('single mode returns the base catalog entry unchanged', () => {
    expect(buildAgentConfig('grok', 'single', 3, INFO)).toEqual(INFO.catalog.grok)
  })
  it('self-consensus adds consensus: N (clamped)', () => {
    expect(buildAgentConfig('grok', 'self', 4, INFO)).toMatchObject({ consensus: 4 })
    expect(buildAgentConfig('grok', 'self', 1, INFO)).toMatchObject({ consensus: 2 })
  })
  it('panel mode sets consensus: true', () => {
    expect(buildAgentConfig('grok', 'panel', 3, INFO)).toMatchObject({ consensus: true })
  })
  it('native mode appends the best-of-n flags to cmd', () => {
    const cfg = buildAgentConfig('grok', 'native', 3, INFO)
    expect(cfg.cmd).toEqual(['grok', '-p', '{prompt}', '--best-of-n', '3'])
  })
  it('does not mutate the source catalog entry', () => {
    buildAgentConfig('grok', 'native', 3, INFO)
    expect(INFO.catalog.grok.cmd).toEqual(['grok', '-p', '{prompt}'])
  })
})
