import { apiGet, apiPost } from './api'
import {
  isConversationSummary,
  type ConversationSummary,
} from './chatCompact'
import { newConversationId } from './chatWs'

export type { ConversationSummary } from './chatCompact'

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
  role: 'user' | 'assistant' | 'status'
  content: string
}

export interface AgentThread {
  agent_id: string
  conversation_id: string
  messages: AgentThreadMessage[]
  summaries: ConversationSummary[]
}

export interface CompactResult {
  summary: ConversationSummary
  summaries: ConversationSummary[]
  raw_count?: number
}

function isThreadMessage(value: unknown): value is AgentThreadMessage {
  if (!value || typeof value !== 'object') return false
  const row = value as { role?: unknown; content?: unknown }
  return (
    (row.role === 'user' || row.role === 'assistant' || row.role === 'status') &&
    typeof row.content === 'string'
  )
}

function parseSummaries(value: unknown): ConversationSummary[] {
  return Array.isArray(value) ? value.filter(isConversationSummary) : []
}

/** GET /chat/thread/?agent= — empty on auth/network failure (chat still works). */
export async function fetchAgentThread(
  agentId: string,
  conversationIdOverride?: string,
): Promise<AgentThread> {
  const agent = agentIdFromBlueprint(agentId)
  const conversationId =
    (conversationIdOverride || '').trim() || conversationIdForAgent(agent)
  try {
    const data = await apiGet<AgentThread>(
      `/chat/thread/?agent=${encodeURIComponent(agent)}&conversation_id=${encodeURIComponent(conversationId)}`,
    )
    const messages = Array.isArray(data?.messages)
      ? data.messages.filter(isThreadMessage)
      : []
    return {
      agent_id: typeof data?.agent_id === 'string' ? data.agent_id : agent,
      conversation_id:
        typeof data?.conversation_id === 'string' && data.conversation_id
          ? data.conversation_id
          : conversationId,
      messages,
      summaries: parseSummaries(data?.summaries),
    }
  } catch {
    return {
      agent_id: agent,
      conversation_id: conversationId,
      messages: [],
      summaries: [],
    }
  }
}

/** POST /chat/compact/ — summarise the backlog. Raw transcript stays on disk. */
export async function compactAgentThread(opts: {
  conversationId: string
  agentId: string
  messages: AgentThreadMessage[]
  spanStart?: number
  spanEnd?: number
}): Promise<CompactResult> {
  const agent = agentIdFromBlueprint(opts.agentId)
  const data = await apiPost<CompactResult>('/chat/compact/', {
    conversation_id: opts.conversationId,
    agent,
    messages: opts.messages,
    span_start: opts.spanStart,
    span_end: opts.spanEnd,
  })
  const summaries = parseSummaries(data?.summaries)
  const summary = isConversationSummary(data?.summary)
    ? data.summary
    : summaries[summaries.length - 1]
  if (!summary) {
    throw new Error('Compact returned no summary')
  }
  return {
    summary,
    summaries: summaries.length ? summaries : [summary],
    raw_count: data?.raw_count,
  }
}
