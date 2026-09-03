import { afterEach, describe, expect, it } from 'vitest'
import { AGENT_EDITS_KEY, saveAgentEdit } from '../agentEdits'
import type { Blueprint } from '../api'
import {
  agentRole,
  exampleRoleAgents,
  fallbackBlueprintSource,
  normalizeAgentRole,
  showsBlueprintEdit,
} from '../agentRoles'

const codey: Blueprint = {
  id: 'codey',
  object: 'blueprint',
  name: 'Codey',
  description: 'Code assistant',
  abbreviation: null,
  required_mcp_servers: [],
  tags: [],
  installed: true,
  compiled: true,
}

describe('agentRoles', () => {
  afterEach(() => {
    localStorage.removeItem(AGENT_EDITS_KEY)
  })

  it('normalizes aliases and unknown specializations', () => {
    expect(normalizeAgentRole('tool_gate')).toBe('gate')
    expect(normalizeAgentRole('tool-gate')).toBe('gate')
    expect(normalizeAgentRole('reviewer')).toBe('skeptic')
    expect(normalizeAgentRole('support')).toBe('support')
    expect(normalizeAgentRole('Writer')).toBe('default')
    expect(normalizeAgentRole(null)).toBe('default')
  })

  it('detects example roles from id/name when API omits role', () => {
    expect(agentRole({ id: 'support', name: 'Support' })).toBe('support')
    expect(agentRole({ id: 'gate', name: 'Gate' })).toBe('gate')
    expect(agentRole({ id: 'skeptic', name: 'Skeptic' })).toBe('skeptic')
    expect(agentRole(codey)).toBe('default')
  })

  it('honours a persisted role override from the agent editor', () => {
    saveAgentEdit('codey', { role: 'gate' })
    expect(agentRole(codey)).toBe('gate')
  })

  it('injects support, gate, and skeptic ahead of catalog agents', () => {
    const agents = exampleRoleAgents([codey])
    expect(agents.map((agent) => agent.id)).toEqual(['support', 'gate', 'skeptic', 'codey'])
    expect(showsBlueprintEdit(agents[0]!)).toBe(true)
    expect(showsBlueprintEdit(agents[1]!)).toBe(true)
    expect(showsBlueprintEdit(agents[2]!)).toBe(true)
    expect(showsBlueprintEdit(codey)).toBe(false)
  })

  it('fallback recipes show how each example role behaves', () => {
    expect(fallbackBlueprintSource('gate', 'gate')).toMatch(/YES/)
    expect(fallbackBlueprintSource('gate', 'gate')).toMatch(/NO/)
    expect(fallbackBlueprintSource('skeptic', 'skeptic')).toMatch(/SKEPTIC_MAX_RETRIES/)
    expect(fallbackBlueprintSource('support', 'support')).toMatch(/Socratic/)
  })
})
