/** Classify chat agents as API, CLI, or remote (REQ-49). */

export type AgentKind = 'api' | 'cli' | 'remote'

const KINDS = new Set<AgentKind>(['api', 'cli', 'remote'])

export function classifyAgentKind(
  raw: string | null | undefined,
  explicit?: string | null,
): AgentKind {
  if (explicit && KINDS.has(explicit as AgentKind)) {
    return explicit as AgentKind
  }
  const text = (raw ?? '').trim().toLowerCase()
  if (text.startsWith('cli:')) return 'cli'
  if (text.startsWith('remote:') || text.startsWith('placeholder:remote:')) {
    return 'remote'
  }
  return 'api'
}

/** True only for API-agent threads. CLI/remote sessions are owned outside swarm. */
export function canEditAgentMessages(
  raw: string | null | undefined,
  explicit?: string | null,
): boolean {
  return classifyAgentKind(raw, explicit) === 'api'
}
