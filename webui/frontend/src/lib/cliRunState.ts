/**
 * REQ-114 — live “CLI subprocess running” signal for the rail Terminate item.
 *
 * ChatPage publishes when a CLI turn starts/stops. AgentSidebar listens so
 * Terminate is enabled only while a tracked pid / active turn exists.
 */

export const CLI_RUN_STATE_EVENT = 'swarm:cli-run-state'
export const CLI_TERMINATED_EVENT = 'swarm:cli-terminated'
export const CLI_PROCESS_STOPPED_TOAST = 'Process stopped.'
export const CLI_TERMINATED_STATUS = 'Terminated'

const running = new Set<string>()

export function resetCliRunState(): void {
  running.clear()
}

export function peekCliRunning(agentId: string): boolean {
  return Boolean(agentId) && running.has(agentId)
}

export function notifyCliRunState(agentId: string, isRunning: boolean): void {
  if (!agentId) return
  if (isRunning) running.add(agentId)
  else running.delete(agentId)
  try {
    window.dispatchEvent(
      new CustomEvent(CLI_RUN_STATE_EVENT, { detail: { agentId, running: isRunning } }),
    )
  } catch {
    /* window unavailable */
  }
}

export function cliRunStateFromEvent(event: Event): { agentId: string; running: boolean } | null {
  const detail = (event as CustomEvent<{ agentId?: unknown; running?: unknown }>).detail
  if (typeof detail?.agentId !== 'string' || !detail.agentId) return null
  return { agentId: detail.agentId, running: Boolean(detail.running) }
}

export function notifyCliTerminated(agentId: string, conversationId?: string): void {
  if (!agentId) return
  running.delete(agentId)
  try {
    window.dispatchEvent(
      new CustomEvent(CLI_TERMINATED_EVENT, {
        detail: { agentId, conversationId: conversationId || '' },
      }),
    )
    window.dispatchEvent(
      new CustomEvent(CLI_RUN_STATE_EVENT, { detail: { agentId, running: false } }),
    )
  } catch {
    /* window unavailable */
  }
}

export function cliTerminatedFromEvent(
  event: Event,
): { agentId: string; conversationId: string } | null {
  const detail = (event as CustomEvent<{ agentId?: unknown; conversationId?: unknown }>).detail
  if (typeof detail?.agentId !== 'string' || !detail.agentId) return null
  return {
    agentId: detail.agentId,
    conversationId: typeof detail.conversationId === 'string' ? detail.conversationId : '',
  }
}
