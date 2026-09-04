/** Composition roster contract (REQ-20 / REQ-28). Not /v1/teams LLM aliases. */

export const MEMBER_KINDS = ['api', 'cli', 'remote', 'team', 'herdr'] as const
export type MemberKind = (typeof MEMBER_KINDS)[number]

export interface TeamRosterMember {
  id: string
  kind: MemberKind
  role: string
  source: string
  team_id?: string
}

export interface TeamRoster {
  id: string
  object?: 'team_roster'
  name: string
  members: TeamRosterMember[]
  wires?: { handoff: boolean; as_tool: boolean }
}

export function isMemberKind(value: unknown): value is MemberKind {
  return typeof value === 'string' && (MEMBER_KINDS as readonly string[]).includes(value)
}

export function parseRosterMember(raw: unknown): TeamRosterMember | null {
  if (!raw || typeof raw !== 'object') return null
  const row = raw as Record<string, unknown>
  const id = String(row.id || '').trim()
  const kind = String(row.kind || '').trim().toLowerCase()
  if (!id || !isMemberKind(kind)) return null
  const teamId = String(row.team_id || '').trim()
  const member: TeamRosterMember = {
    id,
    kind,
    role: String(row.role || 'default'),
    source: String(row.source || ''),
  }
  if (kind === 'team') {
    member.team_id = teamId || id
  } else if (teamId) {
    member.team_id = teamId
  }
  return member
}

export function parseTeamRoster(raw: unknown): TeamRoster | null {
  if (!raw || typeof raw !== 'object') return null
  const row = raw as Record<string, unknown>
  const id = String(row.id || '').trim()
  const looksLikeRoster =
    row.object === 'team_roster' || Array.isArray(row.members) || Array.isArray(row.agent_team)
  if (!id || !looksLikeRoster) return null
  const membersIn = Array.isArray(row.members)
    ? row.members
    : Array.isArray(row.agent_team)
      ? row.agent_team
      : []
  const members = membersIn.map(parseRosterMember).filter((m): m is TeamRosterMember => m !== null)
  return {
    id,
    object: 'team_roster',
    name: String(row.name || id),
    members,
    wires: {
      handoff: row.wires && typeof row.wires === 'object' ? Boolean((row.wires as { handoff?: unknown }).handoff ?? true) : true,
      as_tool: row.wires && typeof row.wires === 'object' ? Boolean((row.wires as { as_tool?: unknown }).as_tool ?? true) : true,
    },
  }
}

export function parseTeamRosterList(payload: unknown): TeamRoster[] {
  if (!payload || typeof payload !== 'object') return []
  const data = (payload as { data?: unknown }).data
  if (!Array.isArray(data)) return []
  return data.map(parseTeamRoster).filter((r): r is TeamRoster => r !== null)
}

export function childTeamIds(roster: TeamRoster): string[] {
  return roster.members
    .filter((m) => m.kind === 'team')
    .map((m) => m.team_id || m.id)
}

export function nestRosters(rosters: TeamRoster[]): Array<TeamRoster & { children: TeamRoster[] }> {
  const byId = new Map(rosters.map((r) => [r.id, r]))
  const childIds = new Set<string>()
  for (const roster of rosters) {
    for (const id of childTeamIds(roster)) childIds.add(id)
  }
  return rosters
    .filter((r) => !childIds.has(r.id))
    .map((r) => ({
      ...r,
      children: childTeamIds(r)
        .map((id) => byId.get(id))
        .filter((c): c is TeamRoster => Boolean(c)),
    }))
}
