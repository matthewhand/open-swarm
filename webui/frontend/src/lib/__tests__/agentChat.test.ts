import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  DEFAULT_AGENT_ID,
  agentIdFromBlueprint,
  conversationIdForAgent,
  fetchAgentThread,
  lastMessageSnippet,
  lastThreadSnippet,
} from '../agentChat'

describe('agentIdFromBlueprint', () => {
  it('maps empty / whitespace to _default', () => {
    expect(agentIdFromBlueprint('')).toBe(DEFAULT_AGENT_ID)
    expect(agentIdFromBlueprint('  ')).toBe(DEFAULT_AGENT_ID)
    expect(agentIdFromBlueprint(null)).toBe(DEFAULT_AGENT_ID)
    expect(agentIdFromBlueprint('jeeves')).toBe('jeeves')
  })
})

describe('conversationIdForAgent', () => {
  afterEach(() => {
    window.localStorage.clear()
  })

  it('returns the same id for the same agent across calls', () => {
    const first = conversationIdForAgent('codey')
    const second = conversationIdForAgent('codey')
    expect(first).toBe(second)
    expect(conversationIdForAgent('other')).not.toBe(first)
  })
})

describe('lastMessageSnippet', () => {
  it('uses last message content, not a purpose string', () => {
    expect(lastMessageSnippet('  prior answer \n next ')).toBe('prior answer next')
    expect(lastMessageSnippet('{"assistant":"HASS"}')).toBe('Message from HASS')
    expect(
      lastThreadSnippet({
        messages: [
          { role: 'user', content: 'purpose must not win' },
          { role: 'assistant', content: 'latest line' },
        ],
      }),
    ).toBe('latest line')
    expect(lastThreadSnippet({ messages: [] })).toBe('')
  })
})

describe('fetchAgentThread', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
  })

  it('returns server messages when the thread endpoint succeeds', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          agent_id: 'jeeves',
          conversation_id: 'agt-1-jeeves',
          messages: [
            { role: 'user', content: 'hi' },
            { role: 'assistant', content: 'hello' },
          ],
        }),
      } as Response),
    )
    const thread = await fetchAgentThread('jeeves')
    expect(thread.messages).toEqual([
      { role: 'user', content: 'hi' },
      { role: 'assistant', content: 'hello' },
    ])
    expect(thread.conversation_id).toBe('agt-1-jeeves')
  })

  it('returns an empty thread when fetch fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('offline')),
    )
    const thread = await fetchAgentThread('jeeves')
    expect(thread.messages).toEqual([])
    expect(thread.agent_id).toBe('jeeves')
    expect(thread.conversation_id).toBeTruthy()
  })
})
