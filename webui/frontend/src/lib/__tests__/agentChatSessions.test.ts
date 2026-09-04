import { beforeEach, describe, expect, it } from 'vitest'
import {
  AGENT_CHAT_SESSIONS_KEY,
  getOrCreateAgentChatSession,
  loadAgentChatSessions,
  persistableMessages,
  putAgentChatSession,
  threadKeyForAgent,
} from '../agentChatSessions'

describe('agentChatSessions', () => {
  beforeEach(() => {
    localStorage.removeItem(AGENT_CHAT_SESSIONS_KEY)
  })

  it('uses a distinct persisted conversation id per agent', () => {
    const support = getOrCreateAgentChatSession('support')
    const hybrid = getOrCreateAgentChatSession('hybrid_team')
    const skeptic = getOrCreateAgentChatSession('skeptic')
    expect(support.conversationId).toBeTruthy()
    expect(hybrid.conversationId).toBeTruthy()
    expect(skeptic.conversationId).toBeTruthy()
    expect(support.conversationId).not.toBe(hybrid.conversationId)
    expect(hybrid.conversationId).not.toBe(skeptic.conversationId)
    expect(getOrCreateAgentChatSession('support').conversationId).toBe(
      support.conversationId,
    )
  })

  it('restores messages after put + reload', () => {
    const session = getOrCreateAgentChatSession('support')
    putAgentChatSession('support', {
      conversationId: session.conversationId,
      messages: [
        { key: 'u1', role: 'user', text: 'hi support' },
        { key: 'a1', role: 'assistant', text: 'hello from support' },
      ],
    })
    const again = getOrCreateAgentChatSession('support')
    expect(again.conversationId).toBe(session.conversationId)
    expect(again.messages).toEqual([
      { key: 'u1', role: 'user', text: 'hi support' },
      { key: 'a1', role: 'assistant', text: 'hello from support' },
    ])
    expect(loadAgentChatSessions().hybrid_team).toBeUndefined()
  })

  it('drops empty streaming stubs from persistable messages', () => {
    expect(
      persistableMessages([
        { key: 'u1', role: 'user', text: 'hi', streaming: false },
        { key: 'a1', role: 'assistant', text: '', streaming: true },
        { key: 'a2', role: 'assistant', text: 'done', streaming: false },
      ]),
    ).toEqual([
      { key: 'u1', role: 'user', text: 'hi' },
      { key: 'a2', role: 'assistant', text: 'done' },
    ])
  })

  it('treats a blank agent id as its own thread key', () => {
    expect(threadKeyForAgent('')).toBe('')
    expect(threadKeyForAgent('  support  ')).toBe('support')
  })
})
