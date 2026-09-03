import { describe, it, expect } from 'vitest'
import {
  LIVE_TAIL,
  buildSummaryPrompt,
  canCompactAt,
  compactSlice,
  linesFromMessages,
} from '../compact-chat'
import type { ChatMessage } from '../../types/agent'

function msg(i: number, role: 'user' | 'assistant' = 'user'): ChatMessage {
  return {
    key: `m${i}`,
    role,
    text: `turn ${i}`,
    timestamp: new Date(0),
  }
}

describe('compact-chat', () => {
  it('keeps the last three live messages when compacting near the end', () => {
    const messages = [0, 1, 2, 3, 4].map((i) => msg(i, i % 2 ? 'assistant' : 'user'))
    expect(LIVE_TAIL).toBe(3)
    const slice = compactSlice(messages, 4)
    expect(slice?.back.map((m) => m.key)).toEqual(['m0', 'm1'])
    expect(slice?.tail.map((m) => m.key)).toEqual(['m2', 'm3', 'm4'])
  })

  it('compacts exactly to here when enough tail remains', () => {
    const messages = [0, 1, 2, 3, 4, 5].map((i) => msg(i))
    const slice = compactSlice(messages, 2)
    expect(slice?.back.map((m) => m.key)).toEqual(['m0', 'm1'])
    expect(slice?.tail.map((m) => m.key)).toEqual(['m2', 'm3', 'm4', 'm5'])
    expect(canCompactAt(messages, 0)).toBe(false)
    expect(canCompactAt(messages, 2)).toBe(true)
  })

  it('expands a prior summary into original lines', () => {
    const summary: ChatMessage = {
      key: 's',
      role: 'assistant',
      text: 'Earlier we planned a demo.',
      kind: 'summary',
      compacted: [
        { role: 'user', text: 'Ship a demo' },
        { role: 'assistant', text: 'Will do' },
      ],
      timestamp: new Date(0),
    }
    const lines = linesFromMessages([summary, msg(3)])
    expect(lines.map((l) => l.text)).toEqual(['Ship a demo', 'Will do', 'turn 3'])
  })

  it('builds a summary prompt that does not continue the task', () => {
    const prompt = buildSummaryPrompt([{ role: 'user', text: 'hello' }], 'keep the API names')
    expect(prompt).toContain('Do not answer the user')
    expect(prompt).toContain('Additional guidance: keep the API names')
    expect(prompt).toContain('[user]: hello')
  })
})
