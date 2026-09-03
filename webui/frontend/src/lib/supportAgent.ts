import type { Blueprint } from './api'

/** Default Support seat — first + highlighted in the conversation rail. */
export const SUPPORT_AGENT_ID = 'support'
/** Catalog ids that ship for the gate seat (`tool_gate` is an alias). */
export const GATE_AGENT_ID = 'gate'
export const TOOL_GATE_AGENT_ID = 'tool_gate'
export const SKEPTIC_AGENT_ID = 'skeptic'

const GATE_ID_ALIASES = new Set([GATE_AGENT_ID, TOOL_GATE_AGENT_ID, 'tool-gate', 'toolgate'])
const SKEPTIC_ID_ALIASES = new Set([SKEPTIC_AGENT_ID, 'reviewer'])

function stubBlueprint(
  id: string,
  name: string,
  description: string,
  role?: Blueprint['role'],
): Blueprint {
  return {
    id,
    object: 'blueprint',
    name,
    description,
    abbreviation: null,
    required_mcp_servers: [],
    tags: [],
    installed: true,
    compiled: true,
    role,
  }
}

export const SYNTHETIC_SUPPORT: Blueprint = stubBlueprint(
  SUPPORT_AGENT_ID,
  'Support',
  'Talk about the other agents.',
  'support',
)

export const SYNTHETIC_GATE: Blueprint = stubBlueprint(
  GATE_AGENT_ID,
  'Safety',
  'Dangerous? yes/no. Until wired, all approved.',
  'gate',
)

export const SYNTHETIC_SKEPTIC: Blueprint = stubBlueprint(
  SKEPTIC_AGENT_ID,
  'Skeptic',
  'Prompt done? If not, retry.',
  'skeptic',
)

function agentId(agent: { id: string }): string {
  return agent.id.trim().toLowerCase()
}

function agentName(agent: { name?: string | null }): string {
  return (agent.name || '').trim().toLowerCase()
}

export function isSupportAgent(agent: { id: string; name?: string | null }): boolean {
  return agentId(agent) === SUPPORT_AGENT_ID || agentName(agent) === 'support'
}

export function isGateAgent(agent: { id: string; name?: string | null }): boolean {
  const name = agentName(agent)
  return (
    GATE_ID_ALIASES.has(agentId(agent)) ||
    name === 'gate' ||
    name === 'tool gate' ||
    name === 'safety'
  )
}

export function isSkepticAgent(agent: { id: string; name?: string | null }): boolean {
  return SKEPTIC_ID_ALIASES.has(agentId(agent)) || agentName(agent) === 'skeptic'
}

/** Ensure Support / gate / skeptic exist even when /v1/blueprints has no such seat. */
export function ensureSupportAgent(agents: Blueprint[]): Blueprint[] {
  const next = [...agents]
  if (!next.some(isSupportAgent)) next.unshift(SYNTHETIC_SUPPORT)
  if (!next.some(isGateAgent)) next.push(SYNTHETIC_GATE)
  if (!next.some(isSkepticAgent)) next.push(SYNTHETIC_SKEPTIC)
  return next
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
