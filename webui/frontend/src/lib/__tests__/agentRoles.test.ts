import { describe, expect, it } from 'vitest'
import { agentRole, normalizeAgentRole, roleBadges, roleCssClass } from '../agentRoles'

describe('agentRoles', () => {
  it('normalizes aliases including cos', () => {
    expect(normalizeAgentRole('tool_gate')).toBe('gate')
    expect(normalizeAgentRole('reviewer')).toBe('skeptic')
    expect(normalizeAgentRole('chief of staff')).toBe('cos')
    expect(normalizeAgentRole('support')).toBe('support')
    expect(normalizeAgentRole('Writer')).toBe('default')
  })

  it('detects roles from id/name when the API omits role', () => {
    expect(agentRole({ id: 'support', name: 'Support' })).toBe('support')
    expect(agentRole({ id: 'gate', name: 'Gate' })).toBe('gate')
    expect(agentRole({ id: 'skeptic', name: 'Skeptic' })).toBe('skeptic')
    expect(agentRole({ id: 'cos', name: 'CoS' })).toBe('cos')
    expect(agentRole({ id: 'codey', name: 'Codey' })).toBe('default')
  })

  it('exposes border-hook CSS classes and a right-stack badge list', () => {
    expect(roleCssClass('gate')).toBe('os-agent-role-gate')
    expect(roleCssClass('cos')).toBe('os-agent-role-cos')
    expect(roleBadges({ id: 'support', name: 'Support' })).toEqual(['support'])
    expect(roleBadges({ id: 'codey', name: 'Codey' })).toEqual([])
  })
})
