import { apiGet, apiPatch, apiPost, ensureCsrfCookie } from './api'
import { classifyAgentKind, type AgentKind } from './agentKind'
import {
  isConversationSummary,
  type ConversationSummary,
} from './chatCompact'
import { newConversationId } from './chatWs'
import { asTranscriptRole, isStatusRole } from './chatStatus'
import {
  parseTurn,
  parseUiEvent,
  reconstructTranscript,
  splitMixedMessages,
  type ReconstructedMessage,
} from './transcriptReconstruct'

export type { ConversationSummary } from './chatCompact'

/** Blueprint id used when Chat is on “Server default model”. */
export const DEFAULT_AGENT_ID = '_default'

const STORAGE_PREFIX = 'swarm_agent_chat:'
const TASKS_PREFIX = 'swarm_agent_tasks:'

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

function tasksKey(agentId: string): string {
  return `${TASKS_PREFIX}${agentIdFromBlueprint(agentId)}`
}

function readTaskIds(agentId: string): string[] {
  try {
    const raw = window.localStorage.getItem(tasksKey(agentId))
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((id) => typeof id === 'string' && id) : []
  } catch {
    return []
  }
}

function writeTaskIds(agentId: string, ids: string[]): void {
  try {
    window.localStorage.setItem(tasksKey(agentId), JSON.stringify(ids))
  } catch {
    /* best-effort */
  }
}

/** Register a running task session so the rail can show a count. */
export function registerTaskSession(agentId: string, conversationId: string): string[] {
  const agent = agentIdFromBlueprint(agentId)
  const next = readTaskIds(agent)
  if (conversationId && !next.includes(conversationId)) next.push(conversationId)
  writeTaskIds(agent, next)
  return next
}

export function listTaskSessions(agentId: string): string[] {
  return readTaskIds(agentId)
}

export function activeTaskSessionCount(agentId: string): number {
  return listTaskSessions(agentId).length
}

/**
 * Conversation id for one user task / CoS handoff.
 *
 * Off (default): reuse the stable per-agent id.
 * On: mint a new empty session and keep it in the concurrent list.
 */
export function conversationIdForTask(
  agentId: string,
  opts?: { newChatPerTask?: boolean; taskId?: string },
): string {
  if (!opts?.newChatPerTask) {
    return conversationIdForAgent(agentId)
  }
  const minted = opts.taskId?.trim() || newConversationId()
  registerTaskSession(agentId, minted)
  return minted
}

export interface AgentThreadMessage {
  role: 'user' | 'assistant' | 'status'
  content: string
  edited?: boolean
  ts?: string
  kind?: string
}

export interface AgentThread {
  agent_id: string
  conversation_id: string
  messages: AgentThreadMessage[]
  turns?: AgentThreadMessage[]
  ui_events?: AgentThreadMessage[]
  summaries: ConversationSummary[]
  kind?: AgentKind
  editable?: boolean
}

export interface CompactResult {
  summary: ConversationSummary
  summaries: ConversationSummary[]
  raw_count?: number
}

function parseThreadMessage(value: unknown): AgentThreadMessage | null {
  if (!value || typeof value !== 'object') return null
  const row = value as { role?: unknown; content?: unknown; edited?: unknown; ts?: unknown; kind?: unknown }
  if (typeof row.role !== 'string' || typeof row.content !== 'string') return null
  if (row.edited !== undefined && row.edited !== true) return null
  if (row.role !== 'user' && row.role !== 'assistant' && !isStatusRole(row.role)) {
    return null
  }
  const parsed: AgentThreadMessage = {
    role: asTranscriptRole(row.role),
    content: row.content,
  }
  if (row.edited === true) parsed.edited = true
  if (typeof row.ts === 'string' && row.ts) parsed.ts = row.ts
  if (typeof row.kind === 'string' && row.kind) parsed.kind = row.kind
  return parsed
}

function reconstructedToThread(rows: ReconstructedMessage[]): AgentThreadMessage[] {
  return rows.map((row) => {
    const out: AgentThreadMessage = {
      role: row.role === 'assistant' ? 'assistant' : row.role === 'user' ? 'user' : 'status',
      content: row.content,
    }
    if (row.edited) out.edited = true
    if (row.ts) out.ts = row.ts
    if (row.kind) out.kind = row.kind
    return out
  })
}

/** Rebuild chrome from ``turns`` + ``ui_events``; fall back to a mixed list. */
export function messagesFromThreadPayload(data: {
  turns?: unknown
  ui_events?: unknown
  messages?: unknown
}): AgentThreadMessage[] {
  const hasSideChannel = Array.isArray(data.turns) || Array.isArray(data.ui_events)
  if (hasSideChannel) {
    const turns = Array.isArray(data.turns) ? data.turns.map(parseTurn).filter((row): row is NonNullable<typeof row> => row != null) : []
    const events = Array.isArray(data.ui_events)
      ? data.ui_events.map(parseUiEvent).filter((row): row is NonNullable<typeof row> => row != null)
      : []
    return reconstructedToThread(reconstructTranscript(turns, events))
  }
  const mixed = Array.isArray(data.messages) ? data.messages : []
  const split = splitMixedMessages(mixed)
  if (split.ui_events.length) {
    return reconstructedToThread(reconstructTranscript(split.turns, split.ui_events))
  }
  return mixed.map(parseThreadMessage).filter((row): row is AgentThreadMessage => row != null)
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
    const messages = messagesFromThreadPayload(data || {})
    const kind = classifyAgentKind(agent, data?.kind)
    return {
      agent_id: typeof data?.agent_id === 'string' ? data.agent_id : agent,
      conversation_id:
        typeof data?.conversation_id === 'string' && data.conversation_id
          ? data.conversation_id
          : conversationId,
      messages,
      summaries: parseSummaries(data?.summaries),
      kind,
      editable: data?.editable === true || (data?.editable !== false && kind === 'api'),
    }
  } catch {
    const kind = classifyAgentKind(agent)
    return {
      agent_id: agent,
      conversation_id: conversationId,
      messages: [],
      summaries: [],
      kind,
      editable: kind === 'api',
    }
  }
}

export interface PatchAgentMessageRequest {
  index: number
  content: string
  conversation_id?: string
}

/** PATCH /chat/thread/?agent= — persist one edited turn (API agents only). */
export async function patchAgentMessage(
  agentId: string,
  body: PatchAgentMessageRequest,
): Promise<AgentThread> {
  const agent = agentIdFromBlueprint(agentId)
  await ensureCsrfCookie()
  const data = await apiPatch<AgentThread>(
    `/chat/thread/?agent=${encodeURIComponent(agent)}`,
    body,
  )
  const messages = messagesFromThreadPayload(data || {})
  const kind = classifyAgentKind(agent, data?.kind)
  return {
    agent_id: typeof data?.agent_id === 'string' ? data.agent_id : agent,
    conversation_id:
      typeof data?.conversation_id === 'string' && data.conversation_id
        ? data.conversation_id
        : conversationIdForAgent(agent),
    messages,
    summaries: parseSummaries(data?.summaries),
    kind,
    editable: data?.editable === true || (data?.editable !== false && kind === 'api'),
  }
}

/** POST /chat/thread/?agent= — append chrome (status) or a real turn (REQ-46). */
export async function appendAgentMessage(
  agentId: string,
  message: { role: string; content: string },
  conversationId?: string,
): Promise<AgentThread> {
  const agent = agentIdFromBlueprint(agentId)
  await ensureCsrfCookie()
  const data = await apiPost<AgentThread>(
    `/chat/thread/?agent=${encodeURIComponent(agent)}${conversationId ? `&conversation_id=${encodeURIComponent(conversationId)}` : ''}`,
    { message, conversation_id: conversationId },
  )
  const messages = messagesFromThreadPayload(data || {})
  const kind = classifyAgentKind(agent, data?.kind)
  return {
    agent_id: typeof data?.agent_id === 'string' ? data.agent_id : agent,
    conversation_id:
      typeof data?.conversation_id === 'string' && data.conversation_id
        ? data.conversation_id
        : conversationId || conversationIdForAgent(agent),
    messages,
    summaries: parseSummaries(data?.summaries),
    kind,
    editable: data?.editable === true || (data?.editable !== false && kind === 'api'),
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
    messages: opts.messages.filter((row) => row.role === 'user' || row.role === 'assistant'),
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
