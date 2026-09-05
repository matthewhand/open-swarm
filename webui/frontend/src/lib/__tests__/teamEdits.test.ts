import { afterEach, describe, expect, it } from 'vitest'
import { TEAM_EDITS_KEY, assignedTeamBlueprintId, loadTeamEdit, saveTeamEdit } from '../teamEdits'

describe('teamEdits (REQ-81)', () => {
  afterEach(() => {
    localStorage.removeItem(TEAM_EDITS_KEY)
  })

  it('persists an assigned team blueprint', () => {
    saveTeamEdit('squad', { blueprintId: 'software_dev' })
    expect(loadTeamEdit('squad').blueprintId).toBe('software_dev')
    expect(assignedTeamBlueprintId({ id: 'squad' })).toBe('software_dev')
  })

  it('falls back to a catalog id that matches the team id', () => {
    expect(assignedTeamBlueprintId({ id: 'software_dev' }, ['software_dev', 'codey'])).toBe(
      'software_dev',
    )
    expect(assignedTeamBlueprintId({ id: 'demo-team' }, ['software_dev'])).toBe('')
  })
})
