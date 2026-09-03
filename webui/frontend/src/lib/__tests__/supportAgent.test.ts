import { describe, expect, it } from 'vitest'
import type { Blueprint } from '../api'
import {
  GATE_AGENT_ID,
  SKEPTIC_AGENT_ID,
  SUPPORT_AGENT_ID,
  defaultBlueprintId,
  isGateAgent,
  isSkepticAgent,
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

  it('injects gate and skeptic seats using catalog ids when present', () => {
    const toolGate: Blueprint = { ...codey, id: 'tool_gate', name: 'Gate' }
    const agents = supportFirstAgents([codey, toolGate])
    expect(agents[0]?.id).toBe(SUPPORT_AGENT_ID)
    expect(agents.some((agent) => agent.id === 'tool_gate' && isGateAgent(agent))).toBe(true)
    expect(agents.some((agent) => agent.id === SKEPTIC_AGENT_ID && isSkepticAgent(agent))).toBe(true)
    expect(agents.filter((agent) => isGateAgent(agent))).toHaveLength(1)
    expect(agents.some((agent) => agent.id === GATE_AGENT_ID)).toBe(false)
  })
})
