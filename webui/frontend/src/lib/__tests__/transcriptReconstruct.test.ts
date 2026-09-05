import { describe, expect, it } from 'vitest'
import {
  formatChromeTime,
  reconstructTranscript,
  splitMixedMessages,
} from '../transcriptReconstruct'
import { messagesFromThreadPayload } from '../agentChat'

describe('reconstructTranscript', () => {
  it('rebuilds chrome from a side channel, not a mixed filter', () => {
    const display = reconstructTranscript(
      [
        { role: 'user', content: 'hello', seq: 1, ts: '2026-09-05T12:00:01Z' },
        { role: 'assistant', content: 'hi', seq: 3, ts: '2026-09-05T12:00:03Z' },
      ],
      [
        {
          kind: 'status',
          content: 'CLI: antigravity → grok',
          seq: 0,
          ts: '2026-09-05T12:00:00Z',
        },
        { kind: 'hop', content: 'Messaged 3 Bots', seq: 2, ts: '2026-09-05T12:00:02Z' },
      ],
    )
    expect(display.map((row) => row.content)).toEqual([
      'CLI: antigravity → grok',
      'hello',
      'Messaged 3 Bots',
      'hi',
    ])
    expect(display[0].role).toBe('status')
    expect(display[0].ts).toBe('2026-09-05T12:00:00Z')
  })

  it('splits a leftover mixed list so the UI can still reconstruct', () => {
    const { turns, ui_events } = splitMixedMessages([
      { role: 'status', content: 'Started a new grok session.' },
      { role: 'user', content: 'hi' },
      { role: 'assistant', content: 'hello' },
    ])
    expect(turns.map((row) => row.role)).toEqual(['user', 'assistant'])
    expect(ui_events[0].content).toBe('Started a new grok session.')
    expect(reconstructTranscript(turns, ui_events).map((row) => row.role)).toEqual([
      'status',
      'user',
      'assistant',
    ])
  })
})

describe('messagesFromThreadPayload', () => {
  it('prefers turns + ui_events over a mixed messages list', () => {
    const messages = messagesFromThreadPayload({
      turns: [{ role: 'user', content: 'hi' }],
      ui_events: [{ kind: 'status', role: 'status', content: 'CLI: a → b', ts: '2026-09-05T01:00:00Z' }],
      messages: [{ role: 'user', content: 'should not win' }],
    })
    expect(messages).toEqual([
      { role: 'user', content: 'hi' },
      { role: 'status', content: 'CLI: a → b', ts: '2026-09-05T01:00:00Z', kind: 'status' },
    ])
  })

  it('reconstructs from a legacy mixed messages payload', () => {
    const messages = messagesFromThreadPayload({
      messages: [
        { role: 'info', content: 'Connecting…' },
        { role: 'system', content: 'Session ready.' },
        { role: 'user', content: 'hi' },
      ],
    })
    expect(messages.map((row) => row.role)).toEqual(['status', 'status', 'user'])
    expect(messages[0].content).toBe('Connecting…')
  })
})

describe('formatChromeTime', () => {
  it('formats a valid ISO timestamp', () => {
    expect(formatChromeTime('2026-09-05T12:04:00Z')).toMatch(/\d/)
    expect(formatChromeTime('')).toBe('')
  })
})
