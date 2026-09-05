import { apiGet, apiPatch, apiPost } from './api'
import { agentIdFromBlueprint } from './agentChat'

/** DaisyUI tooltip copy — keep in sync with Issue #393 / REQ-65. */
export const NEW_CHAT_PER_TASK_LABEL = 'New chat per task'

export const NEW_CHAT_PER_TASK_TOOLTIP =
  'Agents reuse one session by default so they remember the thread. Turn this on for a worker that scales out: each task gets a fresh chat, and several can run at once.'

export const AGENT_SETTINGS_CHANGED_EVENT = 'swarm:agent-settings-changed'
export const AGENT_DROPDOWNS_CHANGED_EVENT = 'swarm:agent-dropdowns-changed'
export const OPEN_AGENT_EDITOR_EVENT = 'swarm:open-agent-editor'

const STORAGE_PREFIX = 'swarm_agent_settings:'
export const AGENT_DROPDOWNS_STORAGE_KEY = 'swarm_agent_dropdowns'

/** Header dropdown fields that persist per agent (REQ-180 / #636). */
export const AGENT_DROPDOWN_FIELDS = ['cli', 'model', 'remote', 'blueprint', 'api'] as const
export type AgentDropdownField = (typeof AGENT_DROPDOWN_FIELDS)[number]
export type AgentDropdownChoice = Partial<Record<AgentDropdownField, string>>
export type AgentDropdowns = Record<string, AgentDropdownChoice>

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

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

export function parseAgentDropdownChoice(value: unknown): AgentDropdownChoice | null {
  const rec = asRecord(value)
  if (!rec) return null
  const choice: AgentDropdownChoice = {}
  for (const field of AGENT_DROPDOWN_FIELDS) {
    const raw = rec[field]
    if (typeof raw !== 'string') continue
    const trimmed = raw.trim()
    if (!trimmed) continue
    choice[field] = trimmed
  }
  return Object.keys(choice).length > 0 ? choice : null
}

export function parseAgentDropdowns(raw: unknown): AgentDropdowns {
  const rec = asRecord(raw)
  if (!rec) return {}
  const out: AgentDropdowns = {}
  for (const [agentId, value] of Object.entries(rec)) {
    const id = agentId.trim()
    if (!id) continue
    const choice = parseAgentDropdownChoice(value)
    if (choice) out[id] = choice
  }
  return out
}

function readDropdownMap(): AgentDropdowns {
  try {
    const raw = window.localStorage.getItem(AGENT_DROPDOWNS_STORAGE_KEY)
    if (!raw) return {}
    return parseAgentDropdowns(JSON.parse(raw))
  } catch {
    return {}
  }
}

function writeDropdownMap(map: AgentDropdowns): void {
  try {
    window.localStorage.setItem(AGENT_DROPDOWNS_STORAGE_KEY, JSON.stringify(map))
  } catch {
    /* persistence is best-effort */
  }
}

function emitDropdownsChanged(agentId?: string): void {
  try {
    window.dispatchEvent(
      new CustomEvent(AGENT_DROPDOWNS_CHANGED_EVENT, { detail: { agentId } }),
    )
  } catch {
    /* tests / non-browser */
  }
}

function readLegacyJson(key: string): Record<string, unknown> {
  try {
    const raw = window.localStorage.getItem(key)
    if (!raw) return {}
    return asRecord(JSON.parse(raw)) ?? {}
  } catch {
    return {}
  }
}

/** Import /agents overlay keys so one prefs bag covers both chat surfaces. */
export function seedAgentDropdownsFromLegacyStore(): AgentDropdowns {
  const backends = readLegacyJson('agent_backends')
  const models = readLegacyJson('agent_cli_models')
  const llms = readLegacyJson('agent_llm_profiles')
  const remotes = readLegacyJson('agent_remote_members')
  const blueprints = readLegacyJson('agent_blueprints')
  const ids = new Set([
    ...Object.keys(backends),
    ...Object.keys(models),
    ...Object.keys(llms),
    ...Object.keys(remotes),
    ...Object.keys(blueprints),
  ])
  const out: AgentDropdowns = {}
  for (const id of ids) {
    const choice: AgentDropdownChoice = {}
    const backend = typeof backends[id] === 'string' ? backends[id].trim() : ''
    if (backend.startsWith('cli:')) choice.cli = backend.slice(4)
    if (typeof models[id] === 'string' && models[id].trim()) choice.model = models[id].trim()
    if (typeof llms[id] === 'string' && llms[id].trim()) choice.api = llms[id].trim()
    if (typeof remotes[id] === 'string' && remotes[id].trim()) choice.remote = remotes[id].trim()
    if (typeof blueprints[id] === 'string' && blueprints[id].trim()) {
      choice.blueprint = blueprints[id].trim()
    }
    if (Object.keys(choice).length > 0) out[id] = choice
  }
  return out
}

export function loadAllLocalAgentDropdowns(): AgentDropdowns {
  const stored = readDropdownMap()
  if (Object.keys(stored).length > 0) return stored
  const seeded = seedAgentDropdownsFromLegacyStore()
  if (Object.keys(seeded).length > 0) writeDropdownMap(seeded)
  return seeded
}

export function loadAgentDropdownChoice(agentId: string): AgentDropdownChoice {
  const agent = agentIdFromBlueprint(agentId)
  return loadAllLocalAgentDropdowns()[agent] ?? {}
}

export function applyLocalAgentDropdowns(map: AgentDropdowns): AgentDropdowns {
  const next = parseAgentDropdowns(map)
  writeDropdownMap(next)
  applyAgentDropdownsToLegacyStore(next)
  emitDropdownsChanged()
  return next
}

function applyAgentDropdownsToLegacyStore(map: AgentDropdowns): void {
  const backends = { ...readLegacyJson('agent_backends') }
  const models = { ...readLegacyJson('agent_cli_models') }
  const llms = { ...readLegacyJson('agent_llm_profiles') }
  const remotes = { ...readLegacyJson('agent_remote_members') }
  const blueprints = { ...readLegacyJson('agent_blueprints') }
  for (const [agentId, choice] of Object.entries(map)) {
    if (choice.cli) backends[agentId] = `cli:${choice.cli}`
    if (choice.model) models[agentId] = choice.model
    if (choice.api) llms[agentId] = choice.api
    if (choice.remote) remotes[agentId] = choice.remote
    if (choice.blueprint) blueprints[agentId] = choice.blueprint
  }
  const write = (key: string, value: Record<string, unknown>) => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value))
    } catch {
      /* best-effort */
    }
  }
  write('agent_backends', backends)
  write('agent_cli_models', models)
  write('agent_llm_profiles', llms)
  write('agent_remote_members', remotes)
  write('agent_blueprints', blueprints)
}

export function saveLocalAgentDropdown(
  agentId: string,
  patch: AgentDropdownChoice,
): AgentDropdownChoice {
  const agent = agentIdFromBlueprint(agentId)
  const map = loadAllLocalAgentDropdowns()
  const current = { ...(map[agent] ?? {}) }
  for (const field of AGENT_DROPDOWN_FIELDS) {
    if (patch[field] === undefined) continue
    const trimmed = patch[field].trim()
    if (!trimmed) delete current[field]
    else current[field] = trimmed
  }
  if (Object.keys(current).length === 0) delete map[agent]
  else map[agent] = current
  writeDropdownMap(map)
  emitDropdownsChanged(agent)
  return current
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
