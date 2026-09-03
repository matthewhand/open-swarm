import { describe, expect, it } from 'vitest'
import type { Blueprint } from '../api'
import {
  SUPPORT_AGENT_ID,
  defaultBlueprintId,
  isSupportAgent,
  supportFirstAgents,
} from '../supportAgent'

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

describe('supportAgent helpers', () => {
  it('injects Support first when the catalog has none', () => {
    const agents = supportFirstAgents([codey])
    expect(agents[0]?.id).toBe(SUPPORT_AGENT_ID)
    expect(isSupportAgent(agents[0]!)).toBe(true)
    expect(agents.some((agent) => agent.id === 'codey')).toBe(true)
  })

  it('defaults an empty URL to Support', () => {
    expect(defaultBlueprintId(null)).toBe(SUPPORT_AGENT_ID)
    expect(defaultBlueprintId('codey')).toBe('codey')
  })
})
