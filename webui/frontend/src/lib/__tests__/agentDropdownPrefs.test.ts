import { afterEach, describe, expect, it } from 'vitest'
import {
  AGENT_DROPDOWNS_STORAGE_KEY,
  applyLocalAgentDropdowns,
  loadAgentDropdownChoice,
  loadAllLocalAgentDropdowns,
  parseAgentDropdowns,
  saveLocalAgentDropdown,
  seedAgentDropdownsFromLegacyStore,
} from '../agentSettings'

describe('agent dropdown prefs (REQ-180)', () => {
  afterEach(() => {
    localStorage.clear()
  })

  it('parses safe fields and drops secrets / empty ids', () => {
    expect(
      parseAgentDropdowns({
        cli_agent: { cli: ' grok ', model: 'grok-4', api_key: 'sk-nope', token: 'x' },
        '': { cli: 'agy' },
        remote: { remote: 'omb', blueprint: 'codey', api: 'auxiliary' },
      }),
    ).toEqual({
      cli_agent: { cli: 'grok', model: 'grok-4' },
      remote: { remote: 'omb', blueprint: 'codey', api: 'auxiliary' },
    })
  })

  it('persists per agent and reloads the last choice', () => {
    expect(loadAgentDropdownChoice('cli_agent')).toEqual({})
    expect(saveLocalAgentDropdown('cli_agent', { cli: 'grok', model: 'grok-4' })).toEqual({
      cli: 'grok',
      model: 'grok-4',
    })
    expect(loadAgentDropdownChoice('cli_agent')).toEqual({ cli: 'grok', model: 'grok-4' })
    saveLocalAgentDropdown('cli_agent', { model: '' })
    expect(loadAgentDropdownChoice('cli_agent')).toEqual({ cli: 'grok' })
    expect(JSON.parse(localStorage.getItem(AGENT_DROPDOWNS_STORAGE_KEY) || '{}')).toEqual({
      cli_agent: { cli: 'grok' },
    })
  })

  it('seeds from /agents overlay keys and applies server bags back onto them', () => {
    localStorage.setItem('agent_backends', JSON.stringify({ 'starter-cli': 'cli:agy' }))
    localStorage.setItem('agent_cli_models', JSON.stringify({ 'starter-cli': 'custom-id' }))
    localStorage.setItem('agent_blueprints', JSON.stringify({ router: 'codey' }))
    expect(seedAgentDropdownsFromLegacyStore()).toEqual({
      'starter-cli': { cli: 'agy', model: 'custom-id' },
      router: { blueprint: 'codey' },
    })
    expect(loadAllLocalAgentDropdowns()['starter-cli']).toEqual({
      cli: 'agy',
      model: 'custom-id',
    })
    applyLocalAgentDropdowns({
      'starter-cli': { cli: 'grok', model: 'grok-4' },
      router: { blueprint: 'jeeves', api: 'orchestration' },
    })
    expect(JSON.parse(localStorage.getItem('agent_backends') || '{}')['starter-cli']).toBe(
      'cli:grok',
    )
    expect(JSON.parse(localStorage.getItem('agent_cli_models') || '{}')['starter-cli']).toBe(
      'grok-4',
    )
    expect(JSON.parse(localStorage.getItem('agent_blueprints') || '{}').router).toBe('jeeves')
    expect(JSON.parse(localStorage.getItem('agent_llm_profiles') || '{}').router).toBe(
      'orchestration',
    )
  })
})
