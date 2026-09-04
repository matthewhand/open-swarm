/**
 * One chat thread per agent. Conversation ids and transcripts persist in
 * localStorage so switching AGENTS rows (or favourite tiles) restores that
 * agent's session instead of appending into a global mash.
 */

import { newConversationId } from './chatWs'

export const AGENT_CHAT_SESSIONS_KEY = 'swarm_agent_chat_sessions'

export interface PersistedChatMessage {
  key: string
  role: 'user' | 'assistant'
  text: string
}

export interface AgentChatSession {
  conversationId: string
  messages: PersistedChatMessage[]
}

export type AgentChatSessionMap = Record<string, AgentChatSession>

export function threadKeyForAgent(agentId: string | null | undefined): string {
  return String(agentId || '').trim()
}

function isPersistedMessage(value: unknown): value is PersistedChatMessage {
  if (!value || typeof value !== 'object') return false
  const row = value as PersistedChatMessage
  return (
    typeof row.key === 'string' &&
    row.key.length > 0 &&
    (row.role === 'user' || row.role === 'assistant') &&
    typeof row.text === 'string'
  )
}

function isSession(value: unknown): value is AgentChatSession {
  if (!value || typeof value !== 'object') return false
  const row = value as AgentChatSession
  return (
    typeof row.conversationId === 'string' &&
    row.conversationId.length > 0 &&
    Array.isArray(row.messages) &&
    row.messages.every(isPersistedMessage)
  )
}

export function loadAgentChatSessions(): AgentChatSessionMap {
  try {
    const raw = localStorage.getItem(AGENT_CHAT_SESSIONS_KEY)
    if (!raw) return {}
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
    const out: AgentChatSessionMap = {}
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (isSession(value)) out[key] = value
    }
    return out
  } catch {
    return {}
  }
}

export const AGENT_CHAT_SESSIONS_EVENT = 'swarm:agent-chat-sessions'

export function emitAgentChatSessionsChanged(agentId?: string): void {
  try {
    window.dispatchEvent(
      new CustomEvent(AGENT_CHAT_SESSIONS_EVENT, { detail: { agentId } }),
    )
  } catch {
    /* jsdom / SSR */
  }
}

export function saveAgentChatSessions(sessions: AgentChatSessionMap, agentId?: string): void {
  try {
    localStorage.setItem(AGENT_CHAT_SESSIONS_KEY, JSON.stringify(sessions))
  } catch {
    /* persistence is best-effort */
  }
  emitAgentChatSessionsChanged(agentId)
}

export function persistableMessages(
  messages: Array<{ key: string; role: string; text: string; streaming?: boolean }>,
): PersistedChatMessage[] {
  return messages
    .filter(
      (row) =>
        (row.role === 'user' || row.role === 'assistant') &&
        (row.text.length > 0 || !row.streaming),
    )
    .map((row) => ({ key: row.key, role: row.role as 'user' | 'assistant', text: row.text }))
}

export function getOrCreateAgentChatSession(agentId: string | null | undefined): AgentChatSession {
  const key = threadKeyForAgent(agentId)
  const all = loadAgentChatSessions()
  const existing = all[key]
  if (existing) return existing
  const created: AgentChatSession = {
    conversationId: newConversationId(),
    messages: [],
  }
  all[key] = created
  saveAgentChatSessions(all, key)
  return created
}

export function putAgentChatSession(
  agentId: string | null | undefined,
  session: AgentChatSession,
): void {
  const key = threadKeyForAgent(agentId)
  const all = loadAgentChatSessions()
  all[key] = {
    conversationId: session.conversationId,
    messages: persistableMessages(session.messages),
  }
  saveAgentChatSessions(all, key)
}
