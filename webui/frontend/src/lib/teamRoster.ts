/**
 * Team roster composition helpers (REQ-20).
 *
 * A roster is a drag-drop contract stored in team_rosters.json via
 * /v1/team-rosters/. It is not a teams.json LLM-profile alias.
 */

import type {
  TeamAgent,
  TeamMemberKind,
  TeamMemberRole,
  TeamRoster,
  TeamRosterMember,
  TeamRosterWires,
} from './api'

export const TEAM_MEMBER_KINDS: TeamMemberKind[] = ['api', 'cli', 'remote']
export const TEAM_MEMBER_ROLES: TeamMemberRole[] = ['support', 'gate', 'skeptic', 'default']

export const DEFAULT_TEAM_WIRES: TeamRosterWires = {
  handoff: true,
  as_tool: true,
}

export const TEAM_COMPOSER_OPEN_EVENT = 'swarm:open-team-composer'

export const KIND_LABEL: Record<TeamMemberKind, string> = {
  api: 'API',
  cli: 'CLI',
  remote: 'remote',
}

export const DRAG_MIME = 'application/x-swarm-team-agent'

export const PLACEHOLDER_TEAM_AGENTS: TeamAgent[] = [
  {
    id: 'grok',
    name: 'grok',
    kind: 'cli',
    source: 'placeholder:cli:grok',
    placeholder: true,
    note: 'Placeholder — CLI catalog unavailable.',
  },
  {
    id: 'claude',
    name: 'claude',
    kind: 'cli',
    source: 'placeholder:cli:claude',
    placeholder: true,
    note: 'Placeholder — CLI catalog unavailable.',
  },
  {
    id: 'acp',
    name: 'ACP harness',
    kind: 'remote',
    source: 'placeholder:remote:acp',
    placeholder: true,
    note: 'Placeholder — remote harness API is not in this tree.',
  },
  {
    id: 'ssh-remote',
    name: 'SSH remote',
    kind: 'remote',
    source: 'placeholder:remote:ssh-remote',
    placeholder: true,
    note: 'Placeholder — remote harness API is not in this tree.',
  },
]

export function emptyRosterDraft(name = ''): Omit<TeamRoster, 'id' | 'object'> & { id: string } {
  return {
    id: '',
    name,
    members: [],
    wires: { ...DEFAULT_TEAM_WIRES },
  }
}

export function memberKey(member: Pick<TeamRosterMember, 'kind' | 'id' | 'source'>): string {
  return `${member.kind}:${member.source || member.id}`
}

export function agentToMember(
  agent: TeamAgent,
  role: TeamMemberRole = 'default',
): TeamRosterMember {
  return {
    id: agent.id,
    kind: agent.kind,
    role,
    source: agent.source,
  }
}

export function rosterHasMember(
  members: TeamRosterMember[],
  agent: Pick<TeamRosterMember, 'kind' | 'id' | 'source'>,
): boolean {
  const key = memberKey(agent)
  return members.some((member) => memberKey(member) === key)
}

export function addMember(
  members: TeamRosterMember[],
  agent: TeamAgent,
  role: TeamMemberRole = 'default',
): TeamRosterMember[] {
  if (rosterHasMember(members, agent)) return members
  return [...members, agentToMember(agent, role)]
}

export function removeMember(
  members: TeamRosterMember[],
  agent: Pick<TeamRosterMember, 'kind' | 'id' | 'source'>,
): TeamRosterMember[] {
  const key = memberKey(agent)
  return members.filter((member) => memberKey(member) !== key)
}

export function setMemberRole(
  members: TeamRosterMember[],
  agent: Pick<TeamRosterMember, 'kind' | 'id' | 'source'>,
  role: TeamMemberRole,
): TeamRosterMember[] {
  const key = memberKey(agent)
  return members.map((member) => (memberKey(member) === key ? { ...member, role } : member))
}

export function parseDragAgent(raw: string): TeamAgent | null {
  try {
    const parsed = JSON.parse(raw) as TeamAgent
    if (!parsed?.id || !TEAM_MEMBER_KINDS.includes(parsed.kind)) return null
    if (!parsed.source) return null
    return {
      id: parsed.id,
      name: parsed.name || parsed.id,
      kind: parsed.kind,
      source: parsed.source,
      description: parsed.description,
      placeholder: parsed.placeholder,
    }
  } catch {
    return null
  }
}

export function encodeDragAgent(agent: TeamAgent): string {
  return JSON.stringify({
    id: agent.id,
    name: agent.name,
    kind: agent.kind,
    source: agent.source,
    description: agent.description,
    placeholder: agent.placeholder,
  })
}

export function agentDisplayName(
  agent: Pick<TeamAgent, 'name' | 'id'> | Pick<TeamRosterMember, 'id'>,
): string {
  return 'name' in agent && agent.name ? agent.name : agent.id
}
