/**
 * Multi-agent team rosters for the AGENTS sidepane (REQ-23).
 *
 * Data source (in order): GET /v1/team-rosters/, then /team_rosters.json,
 * then the packaged demo fixture. Never /v1/teams/ (LLM-profile aliases).
 */

export interface TeamRosterMember {
  id: string
  name: string
  kind: string
  role: string
}

export interface TeamRoster {
  id: string
  object: 'team_roster'
  name: string
  description: string
  members: TeamRosterMember[]
}

export const DEMO_TEAM_ROSTER: TeamRoster = {
  id: 'demo-council',
  object: 'team_roster',
  name: 'Demo Council',
  description: 'Example multi-agent roster (not a /v1/teams LLM-profile alias).',
  members: [
    { id: 'planner', name: 'Planner', kind: 'coordinator', role: 'coordinator' },
    { id: 'researcher', name: 'Researcher', kind: 'agent', role: 'researcher' },
    { id: 'writer', name: 'Writer', kind: 'agent', role: 'writer' },
  ],
}

export const TEAM_ROSTERS_API = '/v1/team-rosters/'
export const TEAM_ROSTERS_FILE = '/team_rosters.json'
export const OPEN_TEAMS_SHEET_EVENT = 'swarm:open-teams-sheet'

export function memberKindLabel(member: TeamRosterMember): string {
  const kind = (member.kind || '').trim()
  const role = (member.role || '').trim()
  if (kind && role && kind.toLowerCase() !== role.toLowerCase()) {
    return `${kind} · ${role}`
  }
  return kind || role || 'member'
}

export function isTeamRoster(value: unknown): value is TeamRoster {
  if (!value || typeof value !== 'object') return false
  const row = value as Record<string, unknown>
  if (typeof row.id !== 'string' || !row.id) return false
  if (row.object === 'team' && 'llm_profile' in row && !Array.isArray(row.members)) {
    return false
  }
  if (row.object === 'blueprint') return false
  return row.object === 'team_roster' || Array.isArray(row.members)
}

export function normalizeTeamRoster(value: unknown): TeamRoster | null {
  if (!isTeamRoster(value)) return null
  const row = value as Record<string, unknown>
  const membersRaw = Array.isArray(row.members) ? row.members : []
  const members: TeamRosterMember[] = []
  for (const item of membersRaw) {
    if (!item || typeof item !== 'object') continue
    const member = item as Record<string, unknown>
    const id = typeof member.id === 'string' ? member.id.trim() : ''
    if (!id) continue
    const kind =
      (typeof member.kind === 'string' && member.kind) ||
      (typeof member.role === 'string' && member.role) ||
      'agent'
    const role =
      (typeof member.role === 'string' && member.role) ||
      (typeof member.kind === 'string' && member.kind) ||
      'member'
    members.push({
      id,
      name: typeof member.name === 'string' && member.name ? member.name : id,
      kind,
      role,
    })
  }
  return {
    id: row.id,
    object: 'team_roster',
    name: typeof row.name === 'string' && row.name ? row.name : row.id,
    description: typeof row.description === 'string' ? row.description : '',
    members,
  }
}

function teamsFromPayload(payload: unknown): TeamRoster[] {
  if (!payload || typeof payload !== 'object') return []
  const raw = payload as Record<string, unknown>
  const list = Array.isArray(payload)
    ? payload
    : Array.isArray(raw.data)
      ? raw.data
      : Array.isArray(raw.teams)
        ? raw.teams
        : null
  if (!list) return []
  const teams: TeamRoster[] = []
  for (const item of list) {
    const team = normalizeTeamRoster(item)
    if (team) teams.push(team)
  }
  return teams
}

async function fetchJson(path: string): Promise<unknown | null> {
  try {
    const response = await fetch(path, { headers: { Accept: 'application/json' } })
    if (!response.ok) return null
    return await response.json()
  } catch {
    return null
  }
}

/**
 * Load rosters for the sidepane. A successful GET/file with one or more
 * teams (including empty-member rosters) wins. Otherwise the demo team
 * keeps the sidepane visible.
 */
export async function loadTeamRosters(): Promise<TeamRoster[]> {
  for (const path of [TEAM_ROSTERS_API, TEAM_ROSTERS_FILE]) {
    const payload = await fetchJson(path)
    if (payload == null) continue
    const teams = teamsFromPayload(payload)
    if (teams.length > 0) return teams
  }
  return [{ ...DEMO_TEAM_ROSTER, members: [...DEMO_TEAM_ROSTER.members] }]
}

export function openTeamsSheet(): void {
  try {
    window.dispatchEvent(new CustomEvent(OPEN_TEAMS_SHEET_EVENT))
  } catch {
    /* non-browser (tests) — TeamsSheet may still be opened via props */
  }
}
