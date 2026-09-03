import type { Agent, AvatarEyes, AvatarTheme } from '../types/agent'
import type { RoleAssignments } from './agent-roles'

export const UNSAVED_TEAM_ID = 'unsaved'
export const TEAMS_STORAGE_KEY = 'agent_router_teams'
export const ACTIVE_TEAM_KEY = 'agent_router_active_team'

export interface TeamSnapshot {
  id: string
  name: string
  saved: boolean
  agentIds: string[]
  agents: Agent[]
  renames: Record<string, string>
  purposes: Record<string, string>
  backends: Record<string, string>
  customSections: Record<string, string>
  customOrder: string[]
  favouriteIds: string[]
  chiefOfStaffId: string | null
  avatarThemeByAgent: Record<string, AvatarTheme>
  avatarEyesByAgent: Record<string, AvatarEyes>
  roleAssignments: RoleAssignments
  defaultLlmProfile: string
  llmProfileByAgent: Record<string, string>
  cliModelByAgent: Record<string, string>
  remoteMemberByAgent: Record<string, string>
  frameworkByAgent: Record<string, string>
}

export function emptyUnsavedTeam(): TeamSnapshot {
  return {
    id: UNSAVED_TEAM_ID,
    name: 'Unsaved',
    saved: false,
    agentIds: [],
    agents: [],
    renames: {},
    purposes: {},
    backends: {},
    customSections: {},
    customOrder: [],
    favouriteIds: [],
    chiefOfStaffId: null,
    avatarThemeByAgent: {},
    avatarEyesByAgent: {},
    roleAssignments: {},
    defaultLlmProfile: '',
    llmProfileByAgent: {},
    cliModelByAgent: {},
    remoteMemberByAgent: {},
    frameworkByAgent: {},
  }
}

export function slugifyTeamName(name: string): string {
  const slug = (name || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return slug || 'team'
}

export function uniqueTeamId(name: string, existing: TeamSnapshot[]): string {
  const base = slugifyTeamName(name)
  const taken = new Set(existing.map((t) => t.id))
  taken.add(UNSAVED_TEAM_ID)
  let id = base
  let n = 2
  while (taken.has(id)) {
    id = `${base}-${n}`
    n += 1
  }
  return id
}

export function ensureUnsavedTeam(teams: TeamSnapshot[]): TeamSnapshot[] {
  if (teams.some((t) => t.id === UNSAVED_TEAM_ID)) return teams
  return [emptyUnsavedTeam(), ...teams]
}

export function loadTeamsFromStorage(): TeamSnapshot[] {
  try {
    const raw = localStorage.getItem(TEAMS_STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    const list = Array.isArray(parsed) ? parsed.filter(isTeamSnapshot) : []
    return ensureUnsavedTeam(list)
  } catch {
    return [emptyUnsavedTeam()]
  }
}

export function saveTeamsToStorage(teams: TeamSnapshot[]): void {
  try {
    localStorage.setItem(TEAMS_STORAGE_KEY, JSON.stringify(ensureUnsavedTeam(teams)))
  } catch {
    // best-effort
  }
}

export function loadActiveTeamId(): string {
  try {
    const raw = localStorage.getItem(ACTIVE_TEAM_KEY)
    if (!raw) return UNSAVED_TEAM_ID
    const id = JSON.parse(raw)
    return typeof id === 'string' && id ? id : UNSAVED_TEAM_ID
  } catch {
    return UNSAVED_TEAM_ID
  }
}

export function saveActiveTeamId(id: string): void {
  try {
    localStorage.setItem(ACTIVE_TEAM_KEY, JSON.stringify(id))
  } catch {
    // best-effort
  }
}

export function captureTeam(
  partial: {
    id: string
    name: string
    saved: boolean
    agents: Agent[]
    renames: Record<string, string>
    purposes: Record<string, string>
    backendByAgent: Record<string, string>
    customSections: Record<string, string>
    customOrder: string[]
    favouriteIds: string[]
    chiefOfStaffId: string | null
    avatarThemeByAgent: Record<string, AvatarTheme>
    avatarEyesByAgent: Record<string, AvatarEyes>
    roleAssignments: RoleAssignments
    defaultLlmProfile: string
    llmProfileByAgent: Record<string, string>
    cliModelByAgent: Record<string, string>
    remoteMemberByAgent?: Record<string, string>
    frameworkByAgent?: Record<string, string>
  },
): TeamSnapshot {
  const agentIds = partial.agents.map((a) => a.agent_id)
  return {
    id: partial.id,
    name: partial.name,
    saved: partial.saved,
    agentIds,
    agents: partial.agents.map((a) => ({ ...a })),
    renames: { ...partial.renames },
    purposes: { ...partial.purposes },
    backends: { ...partial.backendByAgent },
    customSections: { ...partial.customSections },
    customOrder: [...(partial.customOrder.length ? partial.customOrder : agentIds)],
    favouriteIds: [...partial.favouriteIds],
    chiefOfStaffId: partial.chiefOfStaffId,
    avatarThemeByAgent: { ...partial.avatarThemeByAgent },
    avatarEyesByAgent: { ...partial.avatarEyesByAgent },
    roleAssignments: { ...partial.roleAssignments },
    defaultLlmProfile: partial.defaultLlmProfile || '',
    llmProfileByAgent: { ...partial.llmProfileByAgent },
    cliModelByAgent: { ...partial.cliModelByAgent },
    remoteMemberByAgent: { ...(partial.remoteMemberByAgent || {}) },
    frameworkByAgent: { ...(partial.frameworkByAgent || {}) },
  }
}

export function agentsForTeam(catalog: Agent[], team: TeamSnapshot | undefined): Agent[] {
  if (!team || !team.saved || team.agentIds.length === 0) {
    return catalog.length > 0 ? catalog : (team?.agents ?? [])
  }
  const live = new Map(catalog.map((a) => [a.agent_id, a]))
  const snapped = new Map((team.agents || []).map((a) => [a.agent_id, a]))
  const out: Agent[] = []
  for (const id of team.agentIds) {
    const agent = live.get(id) || snapped.get(id)
    if (agent) out.push(agent)
  }
  return out
}

export function upsertTeam(teams: TeamSnapshot[], next: TeamSnapshot): TeamSnapshot[] {
  const list = ensureUnsavedTeam(teams)
  const idx = list.findIndex((t) => t.id === next.id)
  if (idx === -1) return [...list, next]
  const copy = [...list]
  copy[idx] = next
  return copy
}

function isTeamSnapshot(value: unknown): value is TeamSnapshot {
  if (!value || typeof value !== 'object') return false
  const t = value as TeamSnapshot
  return typeof t.id === 'string' && Array.isArray(t.agentIds)
}
