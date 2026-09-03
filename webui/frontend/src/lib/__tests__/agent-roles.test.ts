import { describe, it, expect } from 'vitest'
import {
  parseApprovalVerdict,
  rolesHeldBy,
  setRoleAssignment,
  looksLikeToolUse,
  buildSkepticPrompt,
} from '../agent-roles'

describe('agent roles', () => {
  it('assigns a role to another agent and derives who holds it', () => {
    let assignments = setRoleAssignment({}, 'coder', 'socratic_skeptic', 'researcher')
    assignments = setRoleAssignment(assignments, 'coder', 'taskmaster', 'writer')
    expect(assignments.coder.socratic_skeptic).toBe('researcher')
    expect(rolesHeldBy(assignments, 'researcher')).toEqual(['socratic_skeptic'])
    expect(rolesHeldBy(assignments, 'writer')).toEqual(['taskmaster'])
    expect(rolesHeldBy(assignments, 'coder')).toEqual([])
    assignments = setRoleAssignment(assignments, 'coder', 'socratic_skeptic', null)
    expect(assignments.coder.socratic_skeptic).toBeUndefined()
    expect(rolesHeldBy(assignments, 'researcher')).toEqual([])
  })

  it('parses YES/NO approval verdicts', () => {
    expect(parseApprovalVerdict('YES\nThis would rm -rf the workspace.').needsApproval).toBe(true)
    expect(parseApprovalVerdict('No. Harmless explanation.').needsApproval).toBe(false)
    expect(looksLikeToolUse('I will run `sudo rm -rf /tmp/x`')).toBe(true)
    expect(looksLikeToolUse('Here is a summary of the plan.')).toBe(false)
  })

  it('builds a skeptic prompt that does not redo the task', () => {
    const prompt = buildSkepticPrompt('Ship it', 'Done.')
    expect(prompt).toContain('Socratic skeptic')
    expect(prompt).toContain('Do not redo the task')
    expect(prompt).toContain('Ship it')
  })
})
