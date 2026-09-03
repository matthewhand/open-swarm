import type { Blueprint } from './api'

export const SUPPORT_ROLE = 'support'
export const GATE_ROLE = 'gate'
export const SKEPTIC_ROLE = 'skeptic'
export const SUPPORT_ID = 'support'

export type SpecialAgentRole = typeof SUPPORT_ROLE | typeof GATE_ROLE | typeof SKEPTIC_ROLE

const ROLE_RANK: Record<string, number> = {
  [SUPPORT_ROLE]: 0,
  [GATE_ROLE]: 1,
  [SKEPTIC_ROLE]: 2,
}

export function agentRole(agent: Pick<Blueprint, 'id' | 'role'> | null | undefined): string {
  if (!agent) return ''
  const role = String(agent.role || '').trim().toLowerCase()
  if (role) return role
  const id = String(agent.id || '').trim().toLowerCase()
  if (id === SUPPORT_ID || id === GATE_ROLE || id === SKEPTIC_ROLE) return id
  return ''
}

export function isSupportAgent(agent: Pick<Blueprint, 'id' | 'role'> | null | undefined): boolean {
  return agentRole(agent) === SUPPORT_ROLE
}

export function isGateAgent(agent: Pick<Blueprint, 'id' | 'role'> | null | undefined): boolean {
  return agentRole(agent) === GATE_ROLE
}

export function isSkepticAgent(agent: Pick<Blueprint, 'id' | 'role'> | null | undefined): boolean {
  return agentRole(agent) === SKEPTIC_ROLE
}

/** Support first, then gate, then skeptic; remaining order is preserved. */
export function sortSupportFirst<T extends Pick<Blueprint, 'id' | 'role'>>(agents: T[]): T[] {
  return agents
    .map((agent, index) => ({ agent, index }))
    .sort((a, b) => {
      const rankA = ROLE_RANK[agentRole(a.agent)] ?? 10
      const rankB = ROLE_RANK[agentRole(b.agent)] ?? 10
      if (rankA !== rankB) return rankA - rankB
      return a.index - b.index
    })
    .map((entry) => entry.agent)
}

export function findSupportAgent<T extends Pick<Blueprint, 'id' | 'role'>>(agents: T[]): T | undefined {
  return agents.find(isSupportAgent)
}

/** CSS token for a special role row (support / gate / skeptic), else empty. */
export function roleTone(agent: Pick<Blueprint, 'id' | 'role'> | null | undefined): SpecialAgentRole | '' {
  const role = agentRole(agent)
  if (role === SUPPORT_ROLE || role === GATE_ROLE || role === SKEPTIC_ROLE) return role
  return ''
}
