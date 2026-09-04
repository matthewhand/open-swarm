/**
 * Per-agent editor overrides (REQ-58).
 *
 * Agents in the rail are seats. Each seat can be assigned a catalog blueprint,
 * a display name, a role badge, and an optional LLM override. Persistence is
 * localStorage until an agent-edit API exists — same best-effort pattern as
 * hostname / hidden / pinned.
 *
 * Chat identity stays the agent id (`?blueprint=<agentId>`). The assigned
 * blueprint is what the websocket / run uses.
 */

import type { AgentRole } from './api'

export const AGENT_EDITS_KEY = 'swarm_agent_edits'
export const AGENT_EDITS_CHANGED_EVENT = 'swarm:agent-edits-changed'

const AGENT_ROLES: readonly AgentRole[] = ['default', 'support', 'gate', 'skeptic']

function isAgentRole(value: unknown): value is AgentRole {
  return typeof value === 'string' && (AGENT_ROLES as readonly string[]).includes(value)
}

export interface AgentEdit {
  name?: string
  role?: AgentRole
  blueprintId?: string
  llmOverride?: string
  folder?: string
  command?: string
}

export type AgentEditMap = Record<string, AgentEdit>

function readMap(): AgentEditMap {
  try {
    const raw = localStorage.getItem(AGENT_EDITS_KEY)
    if (!raw) return {}
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
    return parsed as AgentEditMap
  } catch {
    return {}
  }
}

function writeMap(map: AgentEditMap): void {
  try {
    localStorage.setItem(AGENT_EDITS_KEY, JSON.stringify(map))
  } catch {
    /* persistence is best-effort */
  }
}

function emitChange(agentId: string): void {
  try {
    window.dispatchEvent(
      new CustomEvent(AGENT_EDITS_CHANGED_EVENT, { detail: { agentId } }),
    )
  } catch {
    /* jsdom / detached window */
  }
}

export function loadAgentEdits(): AgentEditMap {
  return readMap()
}

export function loadAgentEdit(agentId: string): AgentEdit {
  if (!agentId) return {}
  return readMap()[agentId] ?? {}
}

export function saveAgentEdit(agentId: string, patch: AgentEdit): AgentEdit {
  if (!agentId) return {}
  const map = readMap()
  const current = map[agentId] ?? {}
  const next: AgentEdit = { ...current }

  if (patch.name !== undefined) {
    const name = patch.name.trim()
    if (name) next.name = name
    else delete next.name
  }
  if (patch.role !== undefined) {
    const role = isAgentRole(patch.role) ? patch.role : 'default'
    if (role !== 'default') next.role = role
    else delete next.role
  }
  if (patch.blueprintId !== undefined) {
    const blueprintId = patch.blueprintId.trim()
    if (blueprintId && blueprintId !== agentId) next.blueprintId = blueprintId
    else delete next.blueprintId
  }
  if (patch.llmOverride !== undefined) {
    const llm = patch.llmOverride.trim()
    if (llm) next.llmOverride = llm
    else delete next.llmOverride
  }
  if (patch.folder !== undefined) {
    const folder = patch.folder.trim()
    if (folder) next.folder = folder
    else delete next.folder
  }
  if (patch.command !== undefined) {
    const command = patch.command.trim()
    if (command) next.command = command
    else delete next.command
  }

  if (Object.keys(next).length === 0) delete map[agentId]
  else map[agentId] = next
  writeMap(map)
  emitChange(agentId)
  return next
}

/** Catalog blueprint this agent seat runs. Defaults to the agent id. */
export function assignedBlueprintId(agentId: string): string {
  const assigned = loadAgentEdit(agentId).blueprintId?.trim()
  return assigned || agentId
}

/** Display name: editor override, then catalog name, then id. */
export function editedAgentLabel(agent: { id: string; name?: string | null }): string {
  const override = loadAgentEdit(agent.id).name?.trim()
  if (override) return override
  return agent.name || agent.id
}
