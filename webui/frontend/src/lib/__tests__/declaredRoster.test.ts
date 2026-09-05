import { describe, expect, it } from 'vitest'
import { declaredRosterForTeam, facesFromDeclaredRoster } from '../declaredRoster'

const catalog = [
  {
    id: 'software_dev',
    persona_count: 3,
    personas: [{ name: 'Researcher' }, { name: 'Writer' }, { name: 'Reviewer' }],
  },
  { id: 'junk', persona_count: 1, personas: [] },
]

describe('declaredRosterForTeam (REQ-81)', () => {
  it('uses the assigned blueprint personas', () => {
    const roster = declaredRosterForTeam({ id: 'squad', blueprintId: 'software_dev' }, catalog)
    expect(roster?.count).toBe(3)
    expect(roster?.personas.map((p) => p.name)).toEqual(['Researcher', 'Writer', 'Reviewer'])
    expect(facesFromDeclaredRoster(roster!, 'squad')).toHaveLength(3)
  })

  it('garbage / unparsable is one generic face and no invented names', () => {
    const roster = declaredRosterForTeam({ id: 'bad', blueprintId: 'junk' }, catalog)
    expect(roster?.count).toBe(1)
    expect(roster?.personas).toEqual([])
    expect(roster?.generic).toBe(true)
    const faces = facesFromDeclaredRoster(roster!, 'bad')
    expect(faces).toHaveLength(1)
    expect(faces[0]?.name).toBe('')
  })

  it('returns null when the team has no blueprint', () => {
    expect(declaredRosterForTeam({ id: 'demo-team' }, catalog)).toBeNull()
  })
})
