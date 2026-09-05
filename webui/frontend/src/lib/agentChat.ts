import { apiGet, apiPatch, apiPost, ensureCsrfCookie } from './api'
import { classifyAgentKind, type AgentKind } from './agentKind'
import { chatHrefForRowId } from './agentNotifications'
import {
  isConversationSummary,
  type ConversationSummary,
} from './chatCompact'
import { newConversationId } from './chatWs'
import { asTranscriptRole, isStatusRole } from './chatStatus'
import { messagesFromThreadPayload } from './transcriptReconstruct'

export type { ConversationSummary } from './chatCompact'

/** Blueprint id used when Chat is on “Server default model”. */
export const DEFAULT_AGENT_ID = '_default'

const STORAGE_PREFIX = 'swarm_agent_chat:'
const TASKS_PREFIX = 'swarm_agent_tasks:'

/** Last selected swarm conversation id changed (CLI or Django). */
export const AGENT_CONVERSATION_EVENT = 'swarm:agent-conversation'

export function agentIdFromBlueprint(blueprintId: string | null | undefined): string {
  const trimmed = (blueprintId ?? '').trim()
  return trimmed || DEFAULT_AGENT_ID
}

/** Persist the selected conversation id so remount / browse-back restores it. */
export function setConversationIdForAgent(agentId: string, conversationId: string): void {
  const agent = agentIdFromBlueprint(agentId)
  const id = String(conversationId || '').trim()
  if (!id) return
  if (peekConversationIdForAgent(agent) === id) return
  try {
    window.localStorage.setItem(`${STORAGE_PREFIX}${agent}`, id)
  } catch {
    /* private mode / quota */
  }
  try {
    window.dispatchEvent(
      new CustomEvent(AGENT_CONVERSATION_EVENT, {
        detail: { agentId: agent, conversationId: id },
      }),
    )
  } catch {
    /* jsdom / SSR */
  }
}

/** Stable per-agent conversation id (localStorage). Survives reload. */
export function conversationIdForAgent(agentId: string): string {
  const existing = peekConversationIdForAgent(agentId)
  if (existing) return existing
  const minted = newConversationId()
  setConversationIdForAgent(agentId, minted)
  return minted
}

/** Stored conversation id only — does not mint. REQ-82 copy-id. */
export function peekConversationIdForAgent(agentId: string): string | null {
  const key = `${STORAGE_PREFIX}${agentIdFromBlueprint(agentId)}`
  try {
    const existing = window.localStorage.getItem(key)
    return existing && existing.trim() ? existing : null
  } catch {
    return null
  }
}

/** Rail / remount href: keep the last selected session on the URL when known. */
export function agentChatHref(agentId: string): string {
  const agent = agentIdFromBlueprint(agentId)
  const session = peekConversationIdForAgent(agent)
  const base = chatHrefForRowId(agent)
  if (!session) return base
  return `${base}&session=${encodeURIComponent(session)}`
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
  role: 'user' | 'assistant' | 'status' | 'system'
  content: string
  edited?: boolean
  kind?: 'prior_history'
  /** ISO timestamp so status/info chrome can show when it occurred after reload. */
  ts?: string
}

export interface AgentThread {
  agent_id: string
  conversation_id: string
  session_title?: string
  messages: AgentThreadMessage[]
  summaries: ConversationSummary[]
  kind?: AgentKind
  editable?: boolean
  /** Requested session was not on disk/DB — do not silently swap. */
  session_missing?: boolean
}

export interface CompactResult {
  summary: ConversationSummary
  summaries: ConversationSummary[]
  raw_count?: number
}

function parseThreadMessage(value: unknown): AgentThreadMessage | null {
  if (!value || typeof value !== 'object') return null
  const row = value as {
    role?: unknown
    content?: unknown
    edited?: unknown
    kind?: unknown
    ts?: unknown
    timestamp?: unknown
    created_at?: unknown
  }
  if (typeof row.role !== 'string' || typeof row.content !== 'string') return null
  if (row.edited !== undefined && row.edited !== true) return null
  if (row.kind === 'prior_history') {
    const prior: AgentThreadMessage = {
      role: 'system',
      content: row.content,
      kind: 'prior_history',
    }
    if (row.edited === true) prior.edited = true
    return prior
  }
  if (row.role !== 'user' && row.role !== 'assistant' && !isStatusRole(row.role)) {
    return null
  }
  const parsed: AgentThreadMessage = {
    role: asTranscriptRole(row.role),
    content: row.content,
  }
  if (row.edited === true) parsed.edited = true
  const ts = row.ts || row.timestamp || row.created_at
  if (typeof ts === 'string' && ts.trim()) parsed.ts = ts.trim()
  return parsed
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
    const reconstructed = messagesFromThreadPayload(data || {})
    const messages = reconstructed
      .map(parseThreadMessage)
      .filter((row): row is AgentThreadMessage => row != null)
    const kind = classifyAgentKind(agent, data?.kind)
    return {
      agent_id: typeof data?.agent_id === 'string' ? data.agent_id : agent,
      conversation_id:
        typeof data?.conversation_id === 'string' && data.conversation_id
          ? data.conversation_id
          : conversationId,
      session_title: typeof data?.session_title === 'string' ? data.session_title : '',
      messages,
      summaries: parseSummaries(data?.summaries),
      kind,
      editable: data?.editable === true || (data?.editable !== false && kind === 'api'),
      session_missing: data?.session_missing === true,
    }
  } catch {
    const kind = classifyAgentKind(agent)
    return {
      agent_id: agent,
      conversation_id: conversationId,
      session_title: '',
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
  const reconstructed = messagesFromThreadPayload(data || {})
  const messages = reconstructed
    .map(parseThreadMessage)
    .filter((row): row is AgentThreadMessage => row != null)
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

/** POST /chat/thread/?agent= — append a status/turn message (REQ-46). */
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
  const reconstructed = messagesFromThreadPayload(data || {})
  const messages = reconstructed
    .map(parseThreadMessage)
    .filter((row): row is AgentThreadMessage => row != null)
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
  throughMessageId?: string | number
}): Promise<CompactResult> {
  const agent = agentIdFromBlueprint(opts.agentId)
  const data = await apiPost<CompactResult>('/chat/compact/', {
    conversation_id: opts.conversationId,
    agent,
    messages: opts.messages.filter((row) => row.role === 'user' || row.role === 'assistant'),
    span_start: opts.spanStart,
    span_end: opts.spanEnd,
    through_message_id: opts.throughMessageId,
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
