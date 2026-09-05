import { apiGet, apiPatch, apiPost } from './api'
import { agentIdFromBlueprint } from './agentChat'

/** DaisyUI tooltip copy — keep in sync with Issue #393 / REQ-65. */
export const NEW_CHAT_PER_TASK_LABEL = 'New chat per task'

export const NEW_CHAT_PER_TASK_TOOLTIP =
  'Agents reuse one session by default so they remember the thread. Turn this on for a worker that scales out: each task gets a fresh chat, and several can run at once.'

export { USE_SUGGESTIONS_LABEL, USE_SUGGESTIONS_TOOLTIP } from './suggestions'

export const AGENT_SETTINGS_CHANGED_EVENT = 'swarm:agent-settings-changed'
export const OPEN_AGENT_EDITOR_EVENT = 'swarm:open-agent-editor'

const STORAGE_PREFIX = 'swarm_agent_settings:'

export interface AgentSettings {
  agent_id: string
  new_chat_per_task: boolean
  use_suggestions: boolean
  cli_session_id?: string | null
  remote_session_id?: string | null
  active_sessions?: string[]
}

export interface OpenAgentEditorDetail {
  agentId: string
  agentName?: string
}

export interface AgentSettingsChangedDetail {
  agentId: string
  new_chat_per_task?: boolean
  use_suggestions?: boolean
}

export function openAgentEditor(detail: OpenAgentEditorDetail): void {
  window.dispatchEvent(new CustomEvent<OpenAgentEditorDetail>(OPEN_AGENT_EDITOR_EVENT, { detail }))
}

export function localSettingsKey(agentId: string): string {
  return `${STORAGE_PREFIX}${agentIdFromBlueprint(agentId)}`
}

function readLocalSettings(agentId: string): Record<string, unknown> {
  try {
    const raw = window.localStorage.getItem(localSettingsKey(agentId))
    if (!raw) return {}
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
    return parsed as Record<string, unknown>
  } catch {
    return {}
  }
}

export function loadLocalNewChatPerTask(agentId: string): boolean {
  return readLocalSettings(agentId).new_chat_per_task === true
}

export function loadLocalUseSuggestions(agentId: string): boolean {
  return readLocalSettings(agentId).use_suggestions === true
}

function writeLocalSettings(
  agentId: string,
  patch: { new_chat_per_task?: boolean; use_suggestions?: boolean },
): void {
  const agent = agentIdFromBlueprint(agentId)
  try {
    const key = localSettingsKey(agent)
    const parsed = readLocalSettings(agent)
    window.localStorage.setItem(key, JSON.stringify({ ...parsed, ...patch }))
  } catch {
    /* persistence is best-effort */
  }
  try {
    window.dispatchEvent(
      new CustomEvent<AgentSettingsChangedDetail>(AGENT_SETTINGS_CHANGED_EVENT, {
        detail: { agentId: agent, ...patch },
      }),
    )
  } catch {
    /* tests / non-browser */
  }
}

export function saveLocalNewChatPerTask(agentId: string, value: boolean): void {
  writeLocalSettings(agentId, { new_chat_per_task: value })
}

export function saveLocalUseSuggestions(agentId: string, value: boolean): void {
  writeLocalSettings(agentId, { use_suggestions: value })
}

function asSettings(
  agent: string,
  data: Partial<AgentSettings> | null | undefined,
  fallback: { new_chat_per_task: boolean; use_suggestions: boolean },
): AgentSettings {
  return {
    agent_id: typeof data?.agent_id === 'string' ? data.agent_id : agent,
    new_chat_per_task:
      typeof data?.new_chat_per_task === 'boolean' ? data.new_chat_per_task : fallback.new_chat_per_task,
    use_suggestions:
      typeof data?.use_suggestions === 'boolean' ? data.use_suggestions : fallback.use_suggestions,
    cli_session_id: data?.cli_session_id ?? null,
    remote_session_id: data?.remote_session_id ?? null,
    active_sessions: Array.isArray(data?.active_sessions) ? data.active_sessions : [],
  }
}

export async function fetchAgentSettings(agentId: string): Promise<AgentSettings> {
  const agent = agentIdFromBlueprint(agentId)
  const localNew = loadLocalNewChatPerTask(agent)
  const localSuggest = loadLocalUseSuggestions(agent)
  try {
    const data = await apiGet<AgentSettings>(
      `/v1/agents/${encodeURIComponent(agent)}/settings/`,
    )
    const on = data?.new_chat_per_task === true
    const suggest = data?.use_suggestions === true
    saveLocalNewChatPerTask(agent, on)
    saveLocalUseSuggestions(agent, suggest)
    return asSettings(agent, data, { new_chat_per_task: on, use_suggestions: suggest })
  } catch {
    return {
      agent_id: agent,
      new_chat_per_task: localNew,
      use_suggestions: localSuggest,
      active_sessions: [],
    }
  }
}

export async function saveAgentSettings(
  agentId: string,
  patch: { new_chat_per_task?: boolean; use_suggestions?: boolean },
): Promise<AgentSettings> {
  const agent = agentIdFromBlueprint(agentId)
  if (patch.new_chat_per_task !== undefined) {
    saveLocalNewChatPerTask(agent, patch.new_chat_per_task)
  }
  if (patch.use_suggestions !== undefined) {
    saveLocalUseSuggestions(agent, patch.use_suggestions)
  }
  try {
    const data = await apiPatch<AgentSettings>(
      `/v1/agents/${encodeURIComponent(agent)}/settings/`,
      patch,
    )
    return asSettings(agent, data, {
      new_chat_per_task: patch.new_chat_per_task === true || loadLocalNewChatPerTask(agent),
      use_suggestions: patch.use_suggestions === true || loadLocalUseSuggestions(agent),
    })
  } catch {
    return {
      agent_id: agent,
      new_chat_per_task: patch.new_chat_per_task ?? loadLocalNewChatPerTask(agent),
      use_suggestions: patch.use_suggestions ?? loadLocalUseSuggestions(agent),
      active_sessions: [],
    }
  }
}

export interface AllocatedTaskSession {
  agent_id: string
  conversation_id: string
  new_chat_per_task: boolean
  empty: boolean
  resume_external: boolean
}

export async function allocateAgentTaskSession(
  agentId: string,
  taskId?: string,
): Promise<AllocatedTaskSession | null> {
  const agent = agentIdFromBlueprint(agentId)
  try {
    return await apiPost<AllocatedTaskSession>(
      `/v1/agents/${encodeURIComponent(agent)}/sessions/`,
      taskId ? { task_id: taskId } : {},
    )
  } catch {
    return null
  }
}
