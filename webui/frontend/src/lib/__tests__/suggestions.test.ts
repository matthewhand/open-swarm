import { describe, expect, it } from 'vitest'
import {
  parseSuggestions,
  shouldShowSuggestionChips,
  suggestionsUrl,
} from '../suggestions'

describe('parseSuggestions (REQ-85)', () => {
  it('accepts a structured list and JSON object', () => {
    expect(parseSuggestions({ suggestions: ['Ask about setup', 'Try a demo'] })).toEqual([
      'Ask about setup',
      'Try a demo',
    ])
    expect(parseSuggestions(['One', 'Two'])).toEqual(['One', 'Two'])
    expect(parseSuggestions('{"suggestions":["Alpha","Beta"]}')).toEqual(['Alpha', 'Beta'])
  })

  it('omits bad or empty lists instead of throwing', () => {
    expect(parseSuggestions(null)).toEqual([])
    expect(parseSuggestions('')).toEqual([])
    expect(parseSuggestions({ suggestions: [] })).toEqual([])
    expect(parseSuggestions({ nope: 1 })).toEqual([])
    expect(parseSuggestions([null, '  '])).toEqual([])
  })

  it('caps at five unique short chips', () => {
    const chips = parseSuggestions(['Same', 'same', 'A'.repeat(120), 'Two', 'Three', 'Four', 'Five', 'Six'])
    expect(chips[0]).toBe('Same')
    expect(chips.length).toBe(5)
    expect(chips[2]!.length).toBeLessThanOrEqual(80)
  })
})

describe('shouldShowSuggestionChips', () => {
  it('requires the toggle and a usable list', () => {
    expect(shouldShowSuggestionChips({ enabled: false, chips: ['Hi'] })).toBe(false)
    expect(shouldShowSuggestionChips({ enabled: true, chips: [] })).toBe(false)
    expect(shouldShowSuggestionChips({ enabled: true, chips: ['Hi'] })).toBe(true)
  })
})

describe('suggestionsUrl', () => {
  it('builds the kickstart and continue endpoints', () => {
    expect(suggestionsUrl('codey')).toBe('/v1/agents/codey/suggestions/?mode=kickstart')
    expect(suggestionsUrl('codey', 'continue')).toBe('/v1/agents/codey/suggestions/?mode=continue')
    expect(suggestionsUrl('codey', 'continue', 'conv-1')).toBe(
      '/v1/agents/codey/suggestions/?mode=continue&conversation_id=conv-1',
    )
  })
})
