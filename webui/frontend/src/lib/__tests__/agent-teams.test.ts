import { describe, it, expect } from 'vitest'
import {
  agentsForTeam,
  captureTeam,
  emptyUnsavedTeam,
  slugifyTeamName,
  uniqueTeamId,
  upsertTeam,
} from '../agent-teams'
import type { Agent } from '../../types/agent'

const router: Agent = {
  agent_id: 'router',
  name: 'Agent Router',
  specialty: 'Coordination',
  color: '#6366f1',
  icon: '🧭',
  type: 'orchestrator',
  group: 'orchestration',
}

const coder: Agent = {
  agent_id: 'coder',
  name: 'Coder',
  specialty: 'Dev',
  color: '#f59e0b',
  icon: '💻',
  type: 'specialist',
  group: 'tools',
}

describe('agent team snapshots', () => {
  it('slugifies names and avoids colliding with unsaved', () => {
    expect(slugifyTeamName('Night Shift')).toBe('night-shift')
    expect(uniqueTeamId('Unsaved', [emptyUnsavedTeam()])).toBe('unsaved-2')
  })

  it('unsaved teams use the live catalog', () => {
    const unsaved = emptyUnsavedTeam()
    expect(agentsForTeam([router, coder], unsaved).map((a) => a.agent_id)).toEqual([
      'router',
      'coder',
    ])
  })

  it('named teams keep membership order and fall back to snapshots', () => {
    const team = captureTeam({
      id: 'desk',
      name: 'Desk',
      saved: true,
      agents: [coder, router],
      renames: { coder: 'Byte' },
      purposes: {},
      backendByAgent: {},
      customSections: {},
      customOrder: ['coder', 'router'],
      favouriteIds: [],
      chiefOfStaffId: null,
      avatarThemeByAgent: {},
      avatarEyesByAgent: {},
      roleAssignments: {},
      defaultLlmProfile: '',
      llmProfileByAgent: {},
      cliModelByAgent: {},
    })
    expect(agentsForTeam([router], team).map((a) => a.agent_id)).toEqual(['coder', 'router'])
  })

  it('upserts without dropping Unsaved', () => {
    const named = { ...emptyUnsavedTeam(), id: 'desk', name: 'Desk', saved: true }
    const teams = upsertTeam([], named)
    expect(teams[0].id).toBe('unsaved')
    expect(teams.some((t) => t.id === 'desk')).toBe(true)
  })
})
