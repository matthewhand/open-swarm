import { describe, expect, it } from 'vitest'
import {
  addMember,
  agentToMember,
  DEFAULT_TEAM_WIRES,
  encodeDragAgent,
  emptyRosterDraft,
  KIND_LABEL,
  memberKey,
  parseDragAgent,
  removeMember,
  rosterHasMember,
  setMemberRole,
} from '../teamRoster'
import type { TeamAgent } from '../api'

const jeeves: TeamAgent = {
  id: 'jeeves',
  name: 'Jeeves',
  kind: 'api',
  source: 'blueprint:jeeves',
}

const grok: TeamAgent = {
  id: 'grok',
  name: 'grok',
  kind: 'cli',
  source: 'cli:grok',
}

describe('team roster contract helpers', () => {
  it('defaults wires both on and starts with an empty roster', () => {
    const draft = emptyRosterDraft()
    expect(draft.members).toEqual([])
    expect(draft.wires).toEqual({ handoff: true, as_tool: true })
    expect(DEFAULT_TEAM_WIRES).toEqual({ handoff: true, as_tool: true })
  })

  it('maps agents to members with kind, role, and source', () => {
    expect(agentToMember(jeeves, 'skeptic')).toEqual({
      id: 'jeeves',
      kind: 'api',
      role: 'skeptic',
      source: 'blueprint:jeeves',
    })
  })

  it('adds a member once and can change role or remove', () => {
    let members = addMember([], jeeves, 'support')
    members = addMember(members, jeeves, 'gate')
    expect(members).toHaveLength(1)
    expect(members[0].role).toBe('support')
    expect(rosterHasMember(members, grok)).toBe(false)
    members = setMemberRole(members, jeeves, 'gate')
    expect(members[0].role).toBe('gate')
    members = removeMember(members, jeeves)
    expect(members).toEqual([])
  })

  it('round-trips drag payload and rejects unknown kinds', () => {
    const raw = encodeDragAgent(grok)
    expect(parseDragAgent(raw)).toMatchObject({ id: 'grok', kind: 'cli' })
    expect(parseDragAgent('{"id":"x","kind":"blueprint","source":"x"}')).toBeNull()
    expect(parseDragAgent('not-json')).toBeNull()
  })

  it('labels kinds as API | CLI | remote', () => {
    expect(KIND_LABEL.api).toBe('API')
    expect(KIND_LABEL.cli).toBe('CLI')
    expect(KIND_LABEL.remote).toBe('remote')
    expect(memberKey(jeeves)).toBe('api:blueprint:jeeves')
  })
})
