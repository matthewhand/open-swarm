import { apiGet, apiPatch, apiPost } from './api'
import { agentIdFromBlueprint } from './agentChat'

/** DaisyUI tooltip copy — keep in sync with Issue #393 / REQ-65. */
export const NEW_CHAT_PER_TASK_LABEL = 'New chat per task'

export const NEW_CHAT_PER_TASK_TOOLTIP =
  'Agents reuse one session by default so they remember the thread. Turn this on for a worker that scales out: each task gets a fresh chat, and several can run at once.'

export const AGENT_SETTINGS_CHANGED_EVENT = 'swarm:agent-settings-changed'
export const OPEN_AGENT_EDITOR_EVENT = 'swarm:open-agent-editor'

const STORAGE_PREFIX = 'swarm_agent_settings:'

export interface AgentSettings {
  agent_id: string
  new_chat_per_task: boolean
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
  new_chat_per_task: boolean
}

export function openAgentEditor(detail: OpenAgentEditorDetail): void {
  window.dispatchEvent(new CustomEvent<OpenAgentEditorDetail>(OPEN_AGENT_EDITOR_EVENT, { detail }))
}

export function localSettingsKey(agentId: string): string {
  return `${STORAGE_PREFIX}${agentIdFromBlueprint(agentId)}`
}

export function loadLocalNewChatPerTask(agentId: string): boolean {
  try {
    const raw = window.localStorage.getItem(localSettingsKey(agentId))
    if (!raw) return false
    const parsed = JSON.parse(raw) as { new_chat_per_task?: unknown }
    return parsed?.new_chat_per_task === true
  } catch {
    return false
  }
}

export function saveLocalNewChatPerTask(agentId: string, value: boolean): void {
  const agent = agentIdFromBlueprint(agentId)
  try {
    const key = localSettingsKey(agent)
    const current = window.localStorage.getItem(key)
    const parsed = current ? (JSON.parse(current) as Record<string, unknown>) : {}
    window.localStorage.setItem(
      key,
      JSON.stringify({ ...parsed, new_chat_per_task: value }),
    )
  } catch {
    /* persistence is best-effort */
  }
  try {
    window.dispatchEvent(
      new CustomEvent<AgentSettingsChangedDetail>(AGENT_SETTINGS_CHANGED_EVENT, {
        detail: { agentId: agent, new_chat_per_task: value },
      }),
    )
  } catch {
    /* tests / non-browser */
  }
}

export async function fetchAgentSettings(agentId: string): Promise<AgentSettings> {
  const agent = agentIdFromBlueprint(agentId)
  const local = loadLocalNewChatPerTask(agent)
  try {
    const data = await apiGet<AgentSettings>(
      `/v1/agents/${encodeURIComponent(agent)}/settings/`,
    )
    const on = data?.new_chat_per_task === true
    saveLocalNewChatPerTask(agent, on)
    return {
      agent_id: typeof data?.agent_id === 'string' ? data.agent_id : agent,
      new_chat_per_task: on,
      cli_session_id: data?.cli_session_id ?? null,
      remote_session_id: data?.remote_session_id ?? null,
      active_sessions: Array.isArray(data?.active_sessions) ? data.active_sessions : [],
    }
  } catch {
    return {
      agent_id: agent,
      new_chat_per_task: local,
      active_sessions: [],
    }
  }
}

export async function saveAgentSettings(
  agentId: string,
  patch: { new_chat_per_task: boolean },
): Promise<AgentSettings> {
  const agent = agentIdFromBlueprint(agentId)
  saveLocalNewChatPerTask(agent, patch.new_chat_per_task)
  try {
    const data = await apiPatch<AgentSettings>(
      `/v1/agents/${encodeURIComponent(agent)}/settings/`,
      patch,
    )
    return {
      agent_id: typeof data?.agent_id === 'string' ? data.agent_id : agent,
      new_chat_per_task: data?.new_chat_per_task === true,
      cli_session_id: data?.cli_session_id ?? null,
      remote_session_id: data?.remote_session_id ?? null,
      active_sessions: Array.isArray(data?.active_sessions) ? data.active_sessions : [],
    }
  } catch {
    return {
      agent_id: agent,
      new_chat_per_task: patch.new_chat_per_task,
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
