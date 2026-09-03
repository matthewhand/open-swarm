import { isSupportAgent } from './supportAgent'

/** First-class rail roles. `cos` is reserved for a later CoS seat. */
export type AgentRole = 'default' | 'support' | 'gate' | 'skeptic' | 'cos'

const ROLE_ALIASES: Record<string, AgentRole> = {
  default: 'default',
  worker: 'default',
  agent: 'default',
  coordinator: 'default',
  support: 'support',
  helper: 'support',
  gate: 'gate',
  tool_gate: 'gate',
  'tool-gate': 'gate',
  toolgate: 'gate',
  skeptic: 'skeptic',
  reviewer: 'skeptic',
  cos: 'cos',
  'chief-of-staff': 'cos',
  chief_of_staff: 'cos',
}

export function normalizeAgentRole(value: unknown): AgentRole {
  if (value == null) return 'default'
  const key = String(value).trim().toLowerCase().replace(/\s+/g, '_')
  if (!key) return 'default'
  return ROLE_ALIASES[key] ?? 'default'
}

export function agentRole(agent: {
  id?: string | null
  name?: string | null
  role?: string | null
}): AgentRole {
  const explicit = normalizeAgentRole(agent.role)
  if (explicit !== 'default') return explicit
  if (isSupportAgent({ id: agent.id || '', name: agent.name })) return 'support'
  const id = (agent.id || '').trim().toLowerCase()
  const name = (agent.name || '').trim().toLowerCase()
  if (id === 'gate' || name === 'gate' || name === 'tool gate') return 'gate'
  if (id === 'skeptic' || name === 'skeptic') return 'skeptic'
  if (id === 'cos' || name === 'cos' || name === 'chief of staff') return 'cos'
  return 'default'
}

/** CSS hook used on the row wrap and on each badge (`os-agent-role-*`). */
export function roleCssClass(role: AgentRole | string): string {
  return `os-agent-role-${normalizeAgentRole(role)}`
}

/** Right-stack badges for the rail row. Empty for ordinary workers. */
export function roleBadges(agent: {
  id?: string | null
  name?: string | null
  role?: string | null
}): AgentRole[] {
  const role = agentRole(agent)
  return role === 'default' ? [] : [role]
}
