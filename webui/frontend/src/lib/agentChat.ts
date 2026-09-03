import { apiGet, apiPost } from './api'
import { STATUS_ROLE, type ChatTranscriptRole } from './chatStatus'
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

export interface AgentThreadMessage {
  role: ChatTranscriptRole
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
    (row.role === 'user' || row.role === 'assistant' || row.role === STATUS_ROLE) &&
    typeof row.content === 'string'
  )
}

/** Append a status line to the per-agent JSON thread (REQ-46 persist path). */
export async function persistStatusEvent(
  agentId: string,
  content: string,
): Promise<void> {
  const text = content.trim()
  if (!text) return
  try {
    await apiPost('/chat/thread/', {
      agent: agentIdFromBlueprint(agentId),
      message: { role: STATUS_ROLE, content: text },
    })
  } catch {
    // Best-effort: the transcript still shows the line locally.
  }
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
