import { describe, expect, it } from 'vitest'
import {
  buildDisplayItems,
  contextTextsForMeter,
  outermostSummaries,
  type ChatBubble,
  type ConversationSummary,
} from '../chatCompact'

function bubble(key: string, role: 'user' | 'assistant', text: string): ChatBubble {
  return { key, role, text, streaming: false }
}

function summary(
  id: number,
  start: number,
  end: number,
  body: string,
  parent: number | null = null,
): ConversationSummary {
  return {
    id,
    conversation_id: 'c1',
    span: { start, end },
    parent_summary_id: parent,
    body,
    created_at: '2026-09-03T00:00:00Z',
    replaced_count: end - start + 1,
  }
}

describe('buildDisplayItems', () => {
  const messages = [
    bubble('1', 'user', 'one'),
    bubble('2', 'assistant', 'two'),
    bubble('3', 'user', 'three'),
    bubble('4', 'assistant', 'four'),
  ]

  it('returns raw bubbles when there are no summaries', () => {
    const items = buildDisplayItems(messages, [])
    expect(items.every((item) => item.kind === 'message')).toBe(true)
    expect(items).toHaveLength(4)
  })

  it('replaces a covered span with a bordered summary item', () => {
    const items = buildDisplayItems(messages, [summary(1, 0, 1, 'first pair')])
    expect(items[0]).toMatchObject({ kind: 'summary', summary: { id: 1, body: 'first pair' } })
    expect(items[1]).toMatchObject({ kind: 'message', message: { text: 'three' } })
    expect(items[2]).toMatchObject({ kind: 'message', message: { text: 'four' } })
  })

  it('nests parent_summary_id so only the outer summary is a top-level item', () => {
    const inner = summary(1, 0, 1, 'inner')
    const outer = summary(2, 0, 3, 'outer', 1)
    const items = buildDisplayItems(messages, [inner, outer])
    expect(items).toHaveLength(1)
    expect(items[0]).toMatchObject({ kind: 'summary', summary: { id: 2, parent_summary_id: 1 } })
    expect(outermostSummaries([inner, outer]).map((row) => row.id)).toEqual([2])
  })
})

describe('contextTextsForMeter', () => {
  it('counts summary body instead of covered raw turns', () => {
    const messages = [bubble('1', 'user', 'aaaaaaaa'), bubble('2', 'assistant', 'bbbbbbbb')]
    const texts = contextTextsForMeter(messages, [summary(1, 0, 1, 'short')])
    expect(texts).toEqual(['short'])
  })
})
