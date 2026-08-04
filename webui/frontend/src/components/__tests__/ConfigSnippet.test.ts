import { describe, it, expect } from 'vitest'
import { toFilename } from '../ConfigSnippet'

describe('toFilename', () => {
  it('slugs a label to a .json filename', () => {
    expect(toFilename('cli_agents config')).toBe('cli-agents-config.json')
    expect(toFilename('Inference profile request snippet')).toBe('inference-profile-request-snippet.json')
  })
  it('falls back to config.json for empty/symbol-only labels', () => {
    expect(toFilename('   ')).toBe('config.json')
    expect(toFilename('***')).toBe('config.json')
  })
})
