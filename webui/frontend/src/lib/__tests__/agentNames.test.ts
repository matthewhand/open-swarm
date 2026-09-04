import { afterEach, describe, expect, it } from 'vitest'
import {
  AGENT_NAMES_STORAGE_KEY,
  catalogAgentName,
  displayAgentName,
  loadAgentNameOverride,
  saveAgentNameOverride,
} from '../agentNames'

describe('agent name overrides', () => {
  afterEach(() => {
    localStorage.removeItem(AGENT_NAMES_STORAGE_KEY)
  })

  it('saves a per-agent override and clears on empty / catalog default', () => {
    expect(catalogAgentName({ id: 'codey', name: 'Codey' })).toBe('Codey')
    expect(saveAgentNameOverride('codey', 'Coder', 'Codey')).toBe('Coder')
    expect(loadAgentNameOverride('codey')).toBe('Coder')
    expect(displayAgentName({ id: 'codey', name: 'Codey' })).toBe('Coder')
    expect(saveAgentNameOverride('codey', '   ', 'Codey')).toBe('Codey')
    expect(loadAgentNameOverride('codey')).toBeNull()
    expect(displayAgentName({ id: 'codey', name: 'Codey' })).toBe('Codey')
  })
})
