import { describe, expect, it } from 'vitest'
import {
  STARTER_API_ID,
  STARTER_CLI_ID,
  STARTER_REMOTE_ID,
  STARTER_SUPPORT_ID,
  hideAllExceptStarters,
  mergeStarters,
} from '../starter-agents'
import type { Agent } from '../../types/agent'

function agent(id: string): Agent {
  return {
    agent_id: id,
    name: id,
    specialty: '',
    color: '#000',
    icon: '🤖',
    type: 'specialist',
  }
}

describe('starter agents', () => {
  it('prepends Support, CLI, API, and one remote starter', () => {
    const merged = mergeStarters([agent('coder'), agent('researcher')])
    expect(merged.map((a) => a.agent_id).slice(0, 4)).toEqual([
      STARTER_SUPPORT_ID,
      STARTER_CLI_ID,
      STARTER_API_ID,
      STARTER_REMOTE_ID,
    ])
    expect(merged.find((a) => a.agent_id === STARTER_SUPPORT_ID)?.role).toBe('support')
    expect(merged.find((a) => a.agent_id === STARTER_CLI_ID)?.agent_type).toBe('cli')
    expect(merged.find((a) => a.agent_id === STARTER_API_ID)?.agent_type).toBe('api')
    expect(merged.find((a) => a.agent_id === STARTER_REMOTE_ID)?.framework).toBe('openmausbot')
    expect(merged.find((a) => a.agent_id === STARTER_REMOTE_ID)?.name).toBe('Remote agent')
    expect(merged.some((a) => a.agent_id === 'starter-hermes')).toBe(false)
    expect(merged.some((a) => a.agent_id === 'starter-dsh')).toBe(false)
  })

  it('hide-all keeps only the three typed starters visible', () => {
    const ids = mergeStarters([agent('coder')]).map((a) => a.agent_id)
    expect(hideAllExceptStarters(ids)).toEqual(['coder'])
    expect(hideAllExceptStarters(['coder', STARTER_CLI_ID, STARTER_API_ID, STARTER_REMOTE_ID, 'starter-hermes'])).toEqual([
      'coder',
      'starter-hermes',
    ])
  })
})
