import { afterEach, describe, expect, it } from 'vitest'
import {
  CLI_PROCESS_STOPPED_TOAST,
  CLI_RUN_STATE_EVENT,
  CLI_TERMINATED_EVENT,
  CLI_TERMINATED_STATUS,
  cliRunStateFromEvent,
  cliTerminatedFromEvent,
  notifyCliRunState,
  notifyCliTerminated,
  peekCliRunning,
  resetCliRunState,
} from '../cliRunState'

describe('cliRunState (REQ-114)', () => {
  afterEach(() => {
    resetCliRunState()
  })

  it('tracks running agents and emits state events', () => {
    const seen: Array<{ agentId: string; running: boolean }> = []
    const onState = (event: Event) => {
      const detail = cliRunStateFromEvent(event)
      if (detail) seen.push(detail)
    }
    window.addEventListener(CLI_RUN_STATE_EVENT, onState)
    notifyCliRunState('cli_agent', true)
    expect(peekCliRunning('cli_agent')).toBe(true)
    notifyCliRunState('cli_agent', false)
    expect(peekCliRunning('cli_agent')).toBe(false)
    window.removeEventListener(CLI_RUN_STATE_EVENT, onState)
    expect(seen).toEqual([
      { agentId: 'cli_agent', running: true },
      { agentId: 'cli_agent', running: false },
    ])
  })

  it('notifyCliTerminated clears running and names the honest toast/status copy', () => {
    notifyCliRunState('cli_agent', true)
    const terminated: Array<{ agentId: string; conversationId: string }> = []
    const onTerm = (event: Event) => {
      const detail = cliTerminatedFromEvent(event)
      if (detail) terminated.push(detail)
    }
    window.addEventListener(CLI_TERMINATED_EVENT, onTerm)
    notifyCliTerminated('cli_agent', 'conv-1')
    window.removeEventListener(CLI_TERMINATED_EVENT, onTerm)
    expect(peekCliRunning('cli_agent')).toBe(false)
    expect(terminated).toEqual([{ agentId: 'cli_agent', conversationId: 'conv-1' }])
    expect(CLI_PROCESS_STOPPED_TOAST).toBe('Process stopped.')
    expect(CLI_TERMINATED_STATUS).toBe('Terminated')
  })
})
