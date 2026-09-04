import { afterEach, describe, expect, it } from 'vitest'
import {
  conversationIdForAgent,
  estimateTokensInContext,
  formatElapsed,
  formatTokenCount,
  resetConversationThreads,
} from '../chatMeter'

describe('chatMeter', () => {
  afterEach(() => {
    resetConversationThreads()
  })

  it('estimates tokens and formats the laconic footer bits', () => {
    expect(estimateTokensInContext(['abcd', 'efgh'])).toBe(2)
    expect(formatTokenCount(12)).toBe('12')
    expect(formatTokenCount(1500)).toBe('1.5k')
    expect(formatElapsed(1500)).toBe('1s')
    expect(formatElapsed(65_000)).toBe('1m 05s')
  })

  it('keeps a unique conversation id per agent', () => {
    let n = 0
    const mint = () => `id-${++n}`
    const support = conversationIdForAgent('support', mint)
    const codey = conversationIdForAgent('codey', mint)
    expect(support).toBe('id-1')
    expect(codey).toBe('id-2')
    expect(conversationIdForAgent('support', mint)).toBe('id-1')
    expect(support).not.toBe(codey)
  })
})
