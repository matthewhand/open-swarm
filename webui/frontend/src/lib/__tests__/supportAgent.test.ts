import { describe, expect, it } from 'vitest'
import type { Blueprint } from '../api'
import {
  CLICK_BUBBLE_TO_EDIT,
  GATE_AGENT_ID,
  SKEPTIC_AGENT_ID,
  SUPPORT_AGENT_ID,
  SUPPORT_SKILL_FIXTURE,
  SUPPORT_SKILL_NAME,
  buildSupportTurnContext,
  defaultBlueprintId,
  isGateAgent,
  isSkepticAgent,
  isSupportAgent,
  sessionKindForAgent,
  supportFirstAgents,
  supportSkillAttach,
  supportTurnExtras,
  supportTurnGuidance,
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
    const toolGate: Blueprint = { ...codey, id: 'tool_gate', name: 'Safety' }
    const agents = supportFirstAgents([codey, toolGate])
    expect(agents[0]?.id).toBe(SUPPORT_AGENT_ID)
    expect(agents.some((agent) => agent.id === 'tool_gate' && isGateAgent(agent))).toBe(true)
    expect(agents.some((agent) => agent.id === SKEPTIC_AGENT_ID && isSkepticAgent(agent))).toBe(true)
    expect(agents.filter((agent) => isGateAgent(agent))).toHaveLength(1)
    expect(agents.some((agent) => agent.id === GATE_AGENT_ID)).toBe(false)
  })

  it('attaches the session-ownership skill the same way cli_agent does', () => {
    expect(supportSkillAttach()).toEqual({
      model: 'cli_agent',
      params: { skill: SUPPORT_SKILL_NAME },
    })
    expect(supportTurnExtras()).toEqual({ skill: SUPPORT_SKILL_NAME })
  })

  it('includes the distinctive skill fixture in Support context', () => {
    const ctx = buildSupportTurnContext('api')
    expect(ctx).toContain(SUPPORT_SKILL_FIXTURE)
    expect(ctx).toContain(SUPPORT_SKILL_NAME)
  })

  it('does not tell a CLI-mode user to click the bubble to edit', () => {
    expect(supportTurnGuidance('cli').toLowerCase()).not.toContain(CLICK_BUBBLE_TO_EDIT)
    expect(supportTurnGuidance('remote').toLowerCase()).not.toContain(CLICK_BUBBLE_TO_EDIT)
    expect(buildSupportTurnContext('cli')).toContain(SUPPORT_SKILL_FIXTURE)
  })

  it('classifies cli_agent as a CLI session and codey as API', () => {
    expect(sessionKindForAgent({ id: 'cli_agent', tags: ['cli'] })).toBe('cli')
    expect(sessionKindForAgent({ id: 'codey' })).toBe('api')
    expect(sessionKindForAgent({ id: 'harness', tags: ['remote'] })).toBe('remote')
  })
})
