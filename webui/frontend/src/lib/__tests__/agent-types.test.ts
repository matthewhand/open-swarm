import { describe, expect, it } from 'vitest'
import {
  AGENT_TYPE_SECTIONS,
  agentTypeLabel,
  agentTypeOf,
  defaultRemoteMemberId,
  isChiefOfStaffRemoteName,
  remoteMembersOf,
} from '../agent-types'
import { groupAgents } from '../agent-utils'
import type { Agent } from '../../types/agent'

function agent(partial: Partial<Agent>): Agent {
  return {
    agent_id: 'x',
    name: 'X',
    specialty: '',
    color: '#000',
    icon: '🤖',
    type: 'specialist',
    ...partial,
  }
}

describe('agent types', () => {
  it('keeps sidebar section order api, cli, remote', () => {
    expect(AGENT_TYPE_SECTIONS).toEqual(['api', 'cli', 'remote'])
    const grouped = groupAgents([
      agent({ agent_id: 'r', name: 'R', kind: 'remote', agent_type: 'remote' }),
      agent({ agent_id: 'c', name: 'C', kind: 'cli', agent_type: 'cli' }),
      agent({ agent_id: 'a', name: 'A', kind: 'blueprint', group: 'blueprints' }),
    ])
    expect(Object.keys(grouped)).toEqual(['api', 'cli', 'remote'])
    expect(grouped.api.map((row) => row.agent_id)).toEqual(['a'])
    expect(grouped.cli.map((row) => row.agent_id)).toEqual(['c'])
    expect(grouped.remote.map((row) => row.agent_id)).toEqual(['r'])
    const withSupport = groupAgents([
      agent({ agent_id: 'starter-support', name: 'Support', role: 'support', kind: 'api', agent_type: 'api' }),
      agent({ agent_id: 'a', name: 'A', kind: 'blueprint' }),
    ])
    expect(withSupport.api.map((row) => row.agent_id)).toEqual(['a'])
  })

  it('maps kind to api / cli / remote', () => {
    expect(agentTypeOf(agent({ kind: 'builtin' }))).toBe('api')
    expect(agentTypeOf(agent({ kind: 'personality' }))).toBe('api')
    expect(agentTypeOf(agent({ kind: 'swarm' }))).toBe('api')
    expect(agentTypeOf(agent({ kind: 'blueprint' }))).toBe('api')
    expect(agentTypeOf(agent({ kind: 'cli', cli: 'grok' }))).toBe('cli')
    expect(agentTypeOf(agent({ kind: 'remote', framework: 'openmausbot' }))).toBe('remote')
    expect(agentTypeOf(agent({ agent_type: 'cli', kind: 'personality' }))).toBe('cli')
  })

  it('labels API swarms vs LiteLLM vs CLI vs remote', () => {
    expect(agentTypeLabel(agent({ kind: 'builtin' }))).toBe('API · LiteLLM')
    expect(agentTypeLabel(agent({ kind: 'swarm' }))).toBe('API · openai-agents')
    expect(agentTypeLabel(agent({
      kind: 'personality',
      personas: [{ name: 'A' }, { name: 'B' }],
    }))).toBe('API · openai-agents')
    expect(agentTypeLabel(agent({ kind: 'blueprint' }))).toBe('API · blueprint')
    expect(agentTypeLabel(agent({ kind: 'cli', cli: 'agy' }))).toBe('CLI · agy')
    expect(agentTypeLabel(agent({ kind: 'remote', framework: 'openmausbot' }))).toBe('Remote · openmausbot')
  })

  it('defaults OpenMausBot to Chief of Staff under any common spelling', () => {
    expect(isChiefOfStaffRemoteName('Chief of Staff')).toBe(true)
    expect(isChiefOfStaffRemoteName('CoS')).toBe(true)
    expect(isChiefOfStaffRemoteName('chief-of-staff')).toBe(true)
    expect(isChiefOfStaffRemoteName('chiefOfStaff')).toBe(true)
    const parent = agent({
      agent_id: 'openmausbot',
      kind: 'remote',
      agent_type: 'remote',
      framework: 'openmausbot',
    })
    const members = [
      { id: 'night', name: 'Night editor' },
      { id: 'cos-1', name: 'Chief of Staff' },
    ]
    expect(defaultRemoteMemberId(parent, members)).toBe('cos-1')
    const roster = [
      parent,
      agent({
        agent_id: 'openmausbot--night',
        name: 'Night editor',
        kind: 'remote',
        agent_type: 'remote',
        framework: 'openmausbot',
        parent_id: 'openmausbot',
        remote_id: 'night',
      }),
      agent({
        agent_id: 'openmausbot--cos-1',
        name: 'CoS',
        kind: 'remote',
        agent_type: 'remote',
        framework: 'openmausbot',
        parent_id: 'openmausbot',
        remote_id: 'cos-1',
      }),
    ]
    expect(remoteMembersOf(parent, roster).map((m) => m.id)).toEqual(['night', 'cos-1'])
    const starter = agent({
      agent_id: 'starter-remote',
      kind: 'remote',
      agent_type: 'remote',
      framework: 'openmausbot',
    })
    expect(remoteMembersOf(starter, roster).map((m) => m.id)).toEqual(['night', 'cos-1'])
  })
})
