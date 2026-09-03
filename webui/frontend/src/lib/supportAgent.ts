import type { Blueprint } from './api'

/** Default Support seat — first + highlighted in the conversation rail. */
export const SUPPORT_AGENT_ID = 'support'

export const SYNTHETIC_SUPPORT: Blueprint = {
  id: SUPPORT_AGENT_ID,
  object: 'blueprint',
  name: 'Support',
  description: 'Talk about the other agents.',
  abbreviation: null,
  required_mcp_servers: [],
  tags: [],
  installed: true,
  compiled: true,
}

export function isSupportAgent(agent: { id: string; name?: string | null }): boolean {
  const id = agent.id.trim().toLowerCase()
  const name = (agent.name || '').trim().toLowerCase()
  return id === SUPPORT_AGENT_ID || name === 'support'
}

/** Ensure Support exists even when /v1/blueprints has no such seat. */
export function ensureSupportAgent(agents: Blueprint[]): Blueprint[] {
  if (agents.some(isSupportAgent)) return agents
  return [SYNTHETIC_SUPPORT, ...agents]
}

export function sortSupportFirst(agents: Blueprint[]): Blueprint[] {
  return [...agents].sort((a, b) => {
    const as = isSupportAgent(a) ? 0 : 1
    const bs = isSupportAgent(b) ? 0 : 1
    if (as !== bs) return as - bs
    return (a.name || a.id).localeCompare(b.name || b.id)
  })
}

export function supportFirstAgents(agents: Blueprint[]): Blueprint[] {
  return sortSupportFirst(ensureSupportAgent(agents))
}

export function defaultBlueprintId(fromUrl: string | null | undefined): string {
  const trimmed = (fromUrl || '').trim()
  return trimmed.length > 0 ? trimmed : SUPPORT_AGENT_ID
}

export function agentLabel(agent: { id: string; name?: string | null }): string {
  return agent.name || agent.id
}
