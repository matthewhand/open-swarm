import { afterEach, describe, expect, it } from 'vitest'
import { conversationIdForAgent } from '../agentChat'
import {
  CURRENT_CHAT_SCOPE_KEY,
  chatScopeIdFromSearch,
  loadCurrentChatScope,
  publishCurrentChatScope,
  resolveChatScopeId,
} from '../chatScope'
import { teamThreadId } from '../teamRosters'

describe('chatScope', () => {
  afterEach(() => {
    localStorage.removeItem(CURRENT_CHAT_SCOPE_KEY)
    localStorage.removeItem('swarm_agent_chat:support')
    localStorage.removeItem('swarm_agent_chat:codey')
  })

  it('derives team, remote, session, and agent scopes from the URL', () => {
    expect(chatScopeIdFromSearch(new URLSearchParams('team=office'))).toBe(teamThreadId('office'))
    expect(chatScopeIdFromSearch(new URLSearchParams('remote=hermes&session=h1'))).toBe(
      'remote-hermes-h1',
    )
    expect(chatScopeIdFromSearch(new URLSearchParams('session=abc'))).toBe('abc')
    expect(chatScopeIdFromSearch(new URLSearchParams('blueprint=codey'))).toBe(
      conversationIdForAgent('codey'),
    )
  })

  it('prefers the published current chat over the URL', () => {
    publishCurrentChatScope('live-conv')
    expect(loadCurrentChatScope()).toBe('live-conv')
    expect(resolveChatScopeId(new URLSearchParams('blueprint=codey'))).toBe('live-conv')
  })
})
