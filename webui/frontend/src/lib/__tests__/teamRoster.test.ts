import { describe, expect, it } from 'vitest'
import { childTeamIds, nestRosters, parseTeamRoster, parseTeamRosterList } from '../teamRoster'

describe('teamRoster (REQ-28)', () => {
  it('parses kind=team with team_id and ignores blueprint-shaped rows', () => {
    const roster = parseTeamRoster({
      id: 'office',
      object: 'team_roster',
      name: 'Office',
      members: [
        { id: 'research', kind: 'team', team_id: 'research', role: 'default', source: 'team:research' },
        { id: 'w3p1', kind: 'herdr', role: 'default', source: 'herdr:w3:p1' },
      ],
    })
    expect(roster?.members[0]).toMatchObject({ kind: 'team', team_id: 'research' })
    expect(roster?.members[1].kind).toBe('herdr')
    expect(parseTeamRoster({ id: 'codey', name: 'Codey', object: 'blueprint' })).toBeNull()
  })

  it('nests child teams under the parent', () => {
    const list = parseTeamRosterList({
      object: 'list',
      data: [
        {
          id: 'office',
          object: 'team_roster',
          name: 'Office',
          members: [{ id: 'research', kind: 'team', team_id: 'research', role: 'default', source: 'team:research' }],
        },
        {
          id: 'research',
          object: 'team_roster',
          name: 'Research',
          members: [{ id: 'ada', kind: 'api', role: 'default', source: 'blueprint:ada' }],
        },
      ],
    })
    expect(childTeamIds(list[0])).toEqual(['research'])
    const tree = nestRosters(list)
    expect(tree).toHaveLength(1)
    expect(tree[0].id).toBe('office')
    expect(tree[0].children.map((c) => c.id)).toEqual(['research'])
  })
})
