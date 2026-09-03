import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  DEMO_TEAM_ROSTER,
  isTeamRoster,
  loadTeamRosters,
  memberKindLabel,
  normalizeTeamRoster,
  TEAM_ROSTERS_API,
} from '../teamRosters'

describe('team roster helpers', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('rejects /v1/teams LLM-alias rows', () => {
    expect(
      isTeamRoster({
        id: 'alias',
        object: 'team',
        description: 'LLM alias',
        llm_profile: 'default',
      }),
    ).toBe(false)
    expect(normalizeTeamRoster({ id: 'codey', object: 'blueprint' })).toBeNull()
  })

  it('keeps an empty member roster', () => {
    const team = normalizeTeamRoster({
      id: 'empty-squad',
      object: 'team_roster',
      name: 'Empty Squad',
      members: [],
    })
    expect(team?.members).toEqual([])
  })

  it('formats kind/role for the dropdown', () => {
    expect(
      memberKindLabel({ id: 'p', name: 'Planner', kind: 'coordinator', role: 'coordinator' }),
    ).toBe('coordinator')
    expect(
      memberKindLabel({ id: 'r', name: 'Researcher', kind: 'agent', role: 'researcher' }),
    ).toBe('agent · researcher')
  })

  it('uses GET /v1/team-rosters/ and never /v1/teams/', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo) => {
      const url = String(input)
      expect(url).not.toContain('/v1/teams')
      if (url.includes(TEAM_ROSTERS_API)) {
        return {
          ok: true,
          json: async () => ({
            object: 'list',
            data: [{ id: 'empty-squad', object: 'team_roster', name: 'Empty Squad', members: [] }],
          }),
        }
      }
      throw new Error(`unexpected fetch ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    const teams = await loadTeamRosters()
    expect(teams).toHaveLength(1)
    expect(teams[0].id).toBe('empty-squad')
    expect(teams[0].members).toEqual([])
    expect(fetchMock).toHaveBeenCalled()
  })

  it('falls back to the demo team when GET is empty/missing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({}),
      }),
    )
    const teams = await loadTeamRosters()
    expect(teams.map((team) => team.id)).toEqual([DEMO_TEAM_ROSTER.id])
  })
})
