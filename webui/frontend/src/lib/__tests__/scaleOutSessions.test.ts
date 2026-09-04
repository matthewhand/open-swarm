import { afterEach, describe, expect, it } from 'vitest'
import {
  SCALE_OUT_PULSE_MS,
  SCALE_OUT_SESSIONS_STORAGE_KEY,
  filterAgentSessions,
  listAgentSessions,
  saveAgentSessions,
  sessionHref,
  shouldOpenSessionPicker,
  stackAvatarDelayMs,
  stackedAvatarPlan,
  type AgentSession,
} from '../scaleOutSessions'

function session(
  partial: Partial<AgentSession> & Pick<AgentSession, 'id' | 'startedAt'>,
): AgentSession {
  return {
    agentId: 'codey',
    title: partial.title ?? partial.id,
    snippet: partial.snippet ?? '',
    status: partial.status ?? 'running',
    updatedAt: partial.updatedAt ?? partial.startedAt,
    ...partial,
  }
}

describe('scaleOutSessions', () => {
  afterEach(() => {
    localStorage.removeItem(SCALE_OUT_SESSIONS_STORAGE_KEY)
  })

  it('opens the picker only when session count is greater than 1', () => {
    expect(shouldOpenSessionPicker([])).toBe(false)
    expect(shouldOpenSessionPicker([session({ id: 'a', startedAt: 1 })])).toBe(false)
    expect(
      shouldOpenSessionPicker([
        session({ id: 'a', startedAt: 1 }),
        session({ id: 'b', startedAt: 2 }),
      ]),
    ).toBe(true)
  })

  it('caps the rail stack at 3 faces plus a remainder', () => {
    const four = [0, 200, 400, 600].map((startedAt, index) =>
      session({ id: `run-${index}`, startedAt, status: 'running' }),
    )
    const plan = stackedAvatarPlan(four)
    expect(plan.faces).toHaveLength(3)
    expect(plan.remainder).toBe(1)
    expect(plan.delaysMs).toHaveLength(3)
  })

  it('staggers animation delay by startedAt so four faces do not lockstep', () => {
    const startedAt = [1_000, 1_200, 1_400, 1_600]
    const delays = startedAt.map((value) => stackAvatarDelayMs(value, startedAt[0]))
    expect(delays).toEqual([0, 200, 400, 600])
    expect(new Set(delays).size).toBe(4)
    expect(delays.every((ms) => ms < SCALE_OUT_PULSE_MS)).toBe(true)
  })

  it('filters an agent session list by title and snippet', () => {
    const rows = [
      session({ id: 'a', startedAt: 1, title: 'Refactor auth', snippet: 'jwt cookies' }),
      session({ id: 'b', startedAt: 2, title: 'Write tests', snippet: 'vitest rail' }),
    ]
    expect(filterAgentSessions(rows, 'auth')).toEqual([rows[0]])
    expect(filterAgentSessions(rows, 'RAIL')).toEqual([rows[1]])
    expect(filterAgentSessions(rows, 'nope')).toEqual([])
  })

  it('round-trips sessions per agent and builds a chat session href', () => {
    saveAgentSessions('codey', [
      session({ id: 's1', startedAt: 10, title: 'One' }),
      session({ id: 's2', startedAt: 20, title: 'Two' }),
    ])
    expect(listAgentSessions('codey').map((row) => row.id)).toEqual(['s2', 's1'])
    expect(sessionHref('codey', 's2')).toBe('/chat?blueprint=codey&session=s2')
  })
})
