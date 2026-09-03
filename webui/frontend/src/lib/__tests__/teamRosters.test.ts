import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  ALL_MEMBERS_TARGET,
  DEMO_TEAM_ROSTER,
  MANAGE_TEAMS_HREF,
  fetchTeamRosters,
  memberOptionLabel,
  memberTargetLabel,
  parseTeamRosters,
  teamHideId,
  teamThreadId,
} from '../teamRosters'

describe('parseTeamRosters', () => {
  it('reads a list envelope of team_roster objects', () => {
    const parsed = parseTeamRosters({
      object: 'list',
      data: [
        {
          id: 'alpha',
          object: 'team_roster',
          name: 'Alpha',
          description: 'First',
          members: [{ id: 'codey', name: 'Codey', kind: 'agent', role: 'coder' }],
        },
      ],
    })
    expect(parsed).toHaveLength(1)
    expect(parsed[0].id).toBe('alpha')
    expect(parsed[0].members[0]).toEqual({
      id: 'codey',
      name: 'Codey',
      kind: 'agent',
      role: 'coder',
    })
  })

  it('ignores /v1/teams LLM-alias shapes (no members / object=team without roster)', () => {
    expect(
      parseTeamRosters({
        object: 'list',
        data: [{ id: 'alias', object: 'team', description: 'LLM profile', llm_profile: 'gpt' }],
      }),
    ).toEqual([])
  })

  it('ignores blueprint catalog objects so a mixed GET cannot poison the pane', () => {
    expect(
      parseTeamRosters({
        object: 'list',
        data: [
          {
            id: 'codey',
            object: 'blueprint',
            name: 'Codey',
            description: 'Code assistant',
            members: [{ id: 'x', name: 'X' }],
          },
        ],
      }),
    ).toEqual([])
  })

  it('accepts a bare array or { teams } wrapper', () => {
    const team = {
      id: 'beta',
      name: 'Beta',
      members: [{ id: 'stewie', name: 'Stewie' }],
    }
    expect(parseTeamRosters([team])[0].id).toBe('beta')
    expect(parseTeamRosters({ teams: [team] })[0].id).toBe('beta')
  })
})

describe('labels and ids', () => {
  it('labels All members vs a chosen seat', () => {
    const team = {
      id: 'demo-team',
      name: 'Demo Team',
      description: '',
      members: [{ id: 'codey', name: 'Codey', kind: 'agent', role: 'coder' }],
    }
    expect(memberTargetLabel('all', team)).toBe('All members')
    expect(memberTargetLabel('codey', team)).toBe('Codey (agent/coder)')
  })

  it('formats name + kind/role for the unlabeled dropdown', () => {
    expect(memberOptionLabel({ id: 'codey', name: 'Codey', kind: 'agent', role: 'coder' })).toBe(
      'Codey (agent/coder)',
    )
    expect(memberOptionLabel({ id: 'x', name: 'X', role: 'ops' })).toBe('X (ops)')
    expect(memberOptionLabel({ id: 'y', name: 'Y' })).toBe('Y')
  })

  it('namespaces hide ids so a team cannot collide with an agent slug', () => {
    expect(teamHideId('demo-team')).toBe('team:demo-team')
    expect(teamThreadId('demo-team')).toBe('team-demo-team')
  })

  it('keeps All members / Manage Teams constants stable', () => {
    expect(ALL_MEMBERS_TARGET).toBe('all')
    expect(MANAGE_TEAMS_HREF).toBe('/teams/')
  })
})

describe('fetchTeamRosters', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns GET payload when team_rosters.json is present', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          object: 'list',
          data: [
            {
              id: 'live',
              object: 'team_roster',
              name: 'Live',
              description: '',
              members: [{ id: 'a', name: 'A', kind: 'agent', role: 'lead' }],
            },
          ],
        }),
      } as Response),
    )
    const teams = await fetchTeamRosters()
    expect(teams).toHaveLength(1)
    expect(teams[0].id).toBe('live')
  })

  it('falls back to the demo stub when GET is missing or empty', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({}),
      } as Response),
    )
    await expect(fetchTeamRosters()).resolves.toEqual([DEMO_TEAM_ROSTER])
  })
})
