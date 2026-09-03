import { apiGet } from './api'
import { newConversationId } from './chatWs'

/** Blueprint id used when Chat is on “Server default model”. */
export const DEFAULT_AGENT_ID = '_default'

const STORAGE_PREFIX = 'swarm_agent_chat:'

export function agentIdFromBlueprint(blueprintId: string | null | undefined): string {
  const trimmed = (blueprintId ?? '').trim()
  return trimmed || DEFAULT_AGENT_ID
}

/** Stable per-agent conversation id (localStorage). Survives reload. */
export function conversationIdForAgent(agentId: string): string {
  const key = `${STORAGE_PREFIX}${agentIdFromBlueprint(agentId)}`
  try {
    const existing = window.localStorage.getItem(key)
    if (existing) return existing
    const minted = newConversationId()
    window.localStorage.setItem(key, minted)
    return minted
  } catch {
    return newConversationId()
  }
}

export const AGENT_THREAD_QUERY_KEY = 'agent-thread'

export function agentThreadQueryKey(agentId: string) {
  return [AGENT_THREAD_QUERY_KEY, agentIdFromBlueprint(agentId)] as const
}

export interface AgentThreadMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface AgentThread {
  agent_id: string
  conversation_id: string
  messages: AgentThreadMessage[]
}

function isThreadMessage(value: unknown): value is AgentThreadMessage {
  if (!value || typeof value !== 'object') return false
  const row = value as { role?: unknown; content?: unknown }
  return (
    (row.role === 'user' || row.role === 'assistant') &&
    typeof row.content === 'string'
  )
}

/** One-line rail subtitle. Never the blueprint purpose/description. */
export function lastMessageSnippet(content: string | null | undefined): string {
  if (!content) return ''
  const trimmed = content.replace(/\s+/g, ' ').trim()
  if (!trimmed) return ''
  if (trimmed.startsWith('{')) {
    try {
      const parsed = JSON.parse(trimmed) as { assistant?: unknown }
      if (typeof parsed.assistant === 'string' && parsed.assistant.trim()) {
        return `Message from ${parsed.assistant.trim()}`
      }
    } catch {
      /* ordinary text that happens to start with { */
    }
  }
  return trimmed
}

export function lastThreadSnippet(thread: Pick<AgentThread, 'messages'> | null | undefined): string {
  if (!thread?.messages?.length) return ''
  for (let i = thread.messages.length - 1; i >= 0; i -= 1) {
    const snippet = lastMessageSnippet(thread.messages[i]?.content)
    if (snippet) return snippet
  }
  return ''
}

/** GET /chat/thread/?agent= — empty on auth/network failure (chat still works). */
export async function fetchAgentThread(agentId: string): Promise<AgentThread> {
  const agent = agentIdFromBlueprint(agentId)
  try {
    const data = await apiGet<AgentThread>(
      `/chat/thread/?agent=${encodeURIComponent(agent)}`,
    )
    const messages = Array.isArray(data?.messages)
      ? data.messages.filter(isThreadMessage)
      : []
    return {
      agent_id: typeof data?.agent_id === 'string' ? data.agent_id : agent,
      conversation_id:
        typeof data?.conversation_id === 'string' && data.conversation_id
          ? data.conversation_id
          : conversationIdForAgent(agent),
      messages,
    }
  } catch {
    return {
      agent_id: agent,
      conversation_id: conversationIdForAgent(agent),
      messages: [],
    }
  }
}
