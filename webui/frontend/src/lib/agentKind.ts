/** Classify chat agents as API, CLI, or remote (REQ-49 / REQ-203). */

export type AgentKind = 'api' | 'cli' | 'remote'

const KINDS = new Set<AgentKind>(['api', 'cli', 'remote'])

/** Remote implementations — not a fifth user-facing kind (ADR-011). */
const REMOTE_IMPL_IDS = new Set([
  'herdr',
  'hermes',
  'omb',
  'rakazo',
  'openmausbot',
  'openmaus',
  'openmousbot',
  'rakoza',
  'open-swarm',
  'openswarm',
  'open_swarm',
])

export function isRemoteImplId(raw: string | null | undefined): boolean {
  const key = (raw ?? '').trim().toLowerCase()
  if (!key) return false
  if (key.startsWith('herdr:') || key.startsWith('remote:')) return true
  return REMOTE_IMPL_IDS.has(key)
}

export function classifyAgentKind(
  raw: string | null | undefined,
  explicit?: string | null,
): AgentKind {
  if (explicit && KINDS.has(explicit as AgentKind)) {
    return explicit as AgentKind
  }
  if (isRemoteImplId(explicit)) return 'remote'
  const text = (raw ?? '').trim().toLowerCase()
  if (text.startsWith('cli:')) return 'cli'
  if (
    text.startsWith('remote:') ||
    text.startsWith('placeholder:remote:') ||
    text.startsWith('herdr:') ||
    isRemoteImplId(text)
  ) {
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
