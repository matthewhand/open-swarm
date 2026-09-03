import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  DEFAULT_AGENT_ID,
  agentIdFromBlueprint,
  conversationIdForAgent,
  fetchAgentThread,
  patchAgentMessage,
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
    expect(thread.kind).toBe('api')
    expect(thread.editable).toBe(true)
  })

  it('classifies a CLI fixture as not editable when fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const thread = await fetchAgentThread('cli:grok')
    expect(thread.kind).toBe('cli')
    expect(thread.editable).toBe(false)
  })
})

describe('patchAgentMessage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
  })

  it('PATCHes index and content and returns the edited thread', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        agent_id: 'jeeves',
        conversation_id: 'agt-1-jeeves',
        kind: 'api',
        editable: true,
        messages: [
          { role: 'user', content: 'engineered', edited: true },
          { role: 'assistant', content: 'hello' },
        ],
      }),
    } as Response)
    vi.stubGlobal('fetch', fetchMock)
    const thread = await patchAgentMessage('jeeves', { index: 0, content: 'engineered' })
    expect(thread.messages[0]).toEqual({
      role: 'user',
      content: 'engineered',
      edited: true,
    })
    const patchCall = fetchMock.mock.calls.find(
      (call) => String(call[1]?.method || '').toUpperCase() === 'PATCH',
    )
    expect(patchCall).toBeTruthy()
    expect(String(patchCall?.[0])).toContain('/chat/thread/?agent=jeeves')
    expect(JSON.parse(String(patchCall?.[1]?.body))).toEqual({
      index: 0,
      content: 'engineered',
    })
  })
})
