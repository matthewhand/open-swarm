import { describe, expect, it } from 'vitest'
import {
  botCountLabel,
  collapseInterBotHops,
  groupChatItems,
  hopFromAssistantName,
  interBotChatHref,
  parseHandoffAssistant,
  uniqueHopsInOrder,
  type ChatItem,
  type InterBotHop,
} from '../interBot'

function hop(id: string, name: string, pending = false): InterBotHop {
  return hopFromAssistantName(id, name, pending)
}

describe('parseHandoffAssistant', () => {
  it('reads rest-mode handoff JSON and ignores ordinary text', () => {
    expect(parseHandoffAssistant('{"assistant":"HASS"}')).toBe('HASS')
    expect(parseHandoffAssistant('hello')).toBeNull()
    expect(parseHandoffAssistant('{"role":"assistant"}')).toBeNull()
  })
})

describe('collapseInterBotHops', () => {
  it('keeps triple-dot progress with no avatars while any hop is pending', () => {
    expect(collapseInterBotHops([hop('1', 'HASS', true)])).toEqual({ kind: 'progress' })
    expect(
      collapseInterBotHops([hop('1', 'A', false), hop('2', 'B', true)]),
    ).toEqual({ kind: 'progress' })
  })

  it('renders a single-origin hop as Message from once complete', () => {
    const single = hop('1', 'HASS')
    expect(collapseInterBotHops([single])).toEqual({ kind: 'single', hop: single })
  })

  it('collapses sequential completed hops into one Messaged N Bots line', () => {
    const hops = [hop('1', 'A'), hop('2', 'B'), hop('3', 'C'), hop('4', 'D')]
    expect(collapseInterBotHops(hops)).toEqual({ kind: 'multi', hops })
  })
})

describe('groupChatItems', () => {
  it('collapses adjacent hops and leaves bubbles untouched', () => {
    const items: ChatItem[] = [
      { type: 'message', key: 'u', role: 'user', text: 'go', streaming: false },
      { type: 'hop', key: 'h1', hop: hop('1', 'A') },
      { type: 'hop', key: 'h2', hop: hop('2', 'B') },
      { type: 'message', key: 'a', role: 'assistant', text: 'done', streaming: false },
    ]
    const rows = groupChatItems(items)
    expect(rows).toHaveLength(3)
    expect(rows[0]).toMatchObject({ type: 'message' })
    expect(rows[1]).toMatchObject({ type: 'hop-line', line: { kind: 'multi' } })
    expect(rows[1]?.type).toBe('hop-line')
    if (rows[1]?.type === 'hop-line') {
      expect(rows[1].hops).toHaveLength(2)
    }
    expect(rows[2]).toMatchObject({ type: 'message' })
  })
})

describe('interBotChatHref', () => {
  it('uses the same /chat?blueprint= destination as rail jumps', () => {
    expect(interBotChatHref('hass')).toBe('/chat?blueprint=hass')
    expect(interBotChatHref('cli:grok')).toBe('/chat?blueprint=cli%3Agrok')
  })
})

describe('uniqueHopsInOrder', () => {
  it('keeps first-seen hop order and drops later duplicates', () => {
    const hops = [hop('1', 'A'), hop('2', 'B'), hop('3', 'A'), hop('4', 'C')]
    expect(uniqueHopsInOrder(hops).map((row) => row.name)).toEqual(['A', 'B', 'C'])
  })
})

describe('botCountLabel', () => {
  it('pluralizes the consolidated count', () => {
    expect(botCountLabel(1)).toBe('1 Bot')
    expect(botCountLabel(4)).toBe('4 Bots')
  })
})
