import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  DEFAULT_AGENT_ID,
  activeTaskSessionCount,
  agentIdFromBlueprint,
  compactAgentThread,
  conversationIdForAgent,
  conversationIdForTask,
  fetchAgentThread,
  listTaskSessions,
  peekConversationIdForAgent,
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

  it('peeks a stored id without minting', () => {
    expect(peekConversationIdForAgent('codey')).toBeNull()
    const minted = conversationIdForAgent('codey')
    expect(peekConversationIdForAgent('codey')).toBe(minted)
  })

  it('reuses the stored id when new chat per task is off', () => {
    const reused = conversationIdForTask('codey', { newChatPerTask: false })
    expect(reused).toBe(conversationIdForAgent('codey'))
  })

  it('mints a new session per task when on, without sharing transcripts', () => {
    const one = conversationIdForTask('worker', { newChatPerTask: true, taskId: 'alpha' })
    const two = conversationIdForTask('worker', { newChatPerTask: true, taskId: 'beta' })
    expect(one).not.toBe(two)
    expect(one).not.toBe(conversationIdForAgent('worker'))
    expect(listTaskSessions('worker')).toEqual(expect.arrayContaining([one, two]))
    expect(activeTaskSessionCount('worker')).toBeGreaterThanOrEqual(2)
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
            { role: 'status', content: 'Started a new grok session.' },
            { role: 'assistant', content: 'hello' },
          ],
        }),
      } as Response),
    )
    const thread = await fetchAgentThread('jeeves')
    expect(thread.messages).toEqual([
      { role: 'user', content: 'hi' },
      { role: 'status', content: 'Started a new grok session.' },
      { role: 'assistant', content: 'hello' },
    ])
    expect(thread.conversation_id).toBe('agt-1-jeeves')
    expect(thread.summaries).toEqual([])
  })

  it('keeps prior_history as a system archive row', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          agent_id: 'cli_agent',
          conversation_id: 'cli-cli_agent-abc',
          messages: [
            { role: 'system', content: '**User:** old', kind: 'prior_history' },
            { role: 'status', content: 'Switched to grok session sid-1.' },
          ],
        }),
      } as Response),
    )
    const thread = await fetchAgentThread('cli_agent')
    expect(thread.messages).toEqual([
      { role: 'system', content: '**User:** old', kind: 'prior_history' },
      { role: 'status', content: 'Switched to grok session sid-1.' },
    ])
  })

  it('normalises info/system thread rows to status chrome', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          agent_id: 'jeeves',
          conversation_id: 'agt-1-jeeves',
          messages: [
            { role: 'info', content: 'Connecting…' },
            { role: 'system', content: 'Session ready.' },
            { role: 'user', content: 'hi' },
          ],
        }),
      } as Response),
    )
    const thread = await fetchAgentThread('jeeves')
    expect(thread.messages).toEqual([
      { role: 'status', content: 'Connecting…' },
      { role: 'status', content: 'Session ready.' },
      { role: 'user', content: 'hi' },
    ])
  })

  it('returns summaries from the thread endpoint', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          agent_id: 'jeeves',
          conversation_id: 'agt-1-jeeves',
          messages: [{ role: 'user', content: 'hi' }],
          summaries: [
            {
              id: 1,
              conversation_id: 'agt-1-jeeves',
              span: { start: 0, end: 0 },
              parent_summary_id: null,
              body: 'digest',
              created_at: '2026-09-03T00:00:00Z',
              replaced_count: 1,
            },
          ],
        }),
      } as Response),
    )
    const thread = await fetchAgentThread('jeeves')
    expect(thread.summaries).toHaveLength(1)
    expect(thread.summaries[0].body).toBe('digest')
  })

  it('requests a specific conversation id for a scale-out session', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        agent_id: 'codey',
        conversation_id: 'sess-worker-2',
        messages: [],
      }),
    } as Response)
    vi.stubGlobal('fetch', fetchMock)
    const thread = await fetchAgentThread('codey', 'sess-worker-2')
    expect(thread.conversation_id).toBe('sess-worker-2')
    expect(String(fetchMock.mock.calls[0][0])).toContain('conversation_id=sess-worker-2')
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
    expect(thread.summaries).toEqual([])
  })
})

describe('compactAgentThread', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts the backlog and returns the summary tree', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        summary: {
          id: 2,
          conversation_id: 'c1',
          span: { start: 0, end: 1 },
          parent_summary_id: 1,
          body: 'outer',
          created_at: '2026-09-03T00:00:00Z',
          replaced_count: 2,
        },
        summaries: [
          {
            id: 1,
            conversation_id: 'c1',
            span: { start: 0, end: 1 },
            parent_summary_id: null,
            body: 'inner',
            created_at: '2026-09-03T00:00:00Z',
            replaced_count: 2,
          },
          {
            id: 2,
            conversation_id: 'c1',
            span: { start: 0, end: 1 },
            parent_summary_id: 1,
            body: 'outer',
            created_at: '2026-09-03T00:00:00Z',
            replaced_count: 2,
          },
        ],
        raw_count: 2,
      }),
    } as Response)
    vi.stubGlobal('fetch', fetchMock)
    const result = await compactAgentThread({
      conversationId: 'c1',
      agentId: 'jeeves',
      messages: [
        { role: 'user', content: 'hi' },
        { role: 'assistant', content: 'hello' },
      ],
    })
    expect(result.summary.parent_summary_id).toBe(1)
    expect(result.summaries).toHaveLength(2)
    expect(fetchMock).toHaveBeenCalled()
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toBe('/chat/compact/')
    expect(init.method).toBe('POST')
  })
})
