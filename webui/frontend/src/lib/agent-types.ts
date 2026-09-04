import type { Agent } from '../types/agent'

/** How a sidebar agent is run. Mirrors src/swarm/core/agent_types.py. */
export type AgentType = 'api' | 'cli' | 'remote'

export const AGENT_TYPE_SECTIONS: AgentType[] = ['api', 'cli', 'remote']

export const AGENT_TYPE_LABELS: Record<AgentType, string> = {
  api: 'API',
  cli: 'CLI',
  remote: 'Remote',
}

export function agentTypeOf(agent: Pick<Agent, 'agent_type' | 'kind'> | undefined): AgentType {
  if (!agent) return 'api'
  if (agent.agent_type === 'api' || agent.agent_type === 'cli' || agent.agent_type === 'remote') {
    return agent.agent_type
  }
  if (agent.kind === 'cli') return 'cli'
  if (agent.kind === 'remote') return 'remote'
  return 'api'
}

export function agentTypeLabel(agent: Agent | undefined): string {
  if (!agent) return 'API · LiteLLM'
  const t = agentTypeOf(agent)
  if (t === 'cli') return agent.cli ? `CLI · ${agent.cli}` : 'CLI'
  if (t === 'remote') return agent.framework ? `Remote · ${agent.framework}` : 'Remote'
  const personas = agent.personas?.filter((p) => p.name.trim()) ?? []
  if (agent.kind === 'swarm' || personas.length >= 2) return 'API · openai-agents'
  if (agent.kind === 'blueprint') return 'API · blueprint'
  return 'API · LiteLLM'
}

export interface RemoteMemberOption {
  id: string
  name: string
}

function compactToken(value: string): string {
  return value.toLowerCase().replace(/[\s_-]+/g, '')
}

/** Chief of Staff / CoS / chief-of-staff / chiefOfStaff (case-insensitive). */
export function isChiefOfStaffRemoteName(value: string | undefined): boolean {
  const raw = (value || '').trim()
  if (!raw) return false
  const compact = compactToken(raw)
  return compact === 'cos' || compact === 'chiefofstaff'
}

export function remoteMemberIdOf(agent: Pick<Agent, 'remote_id' | 'model' | 'target' | 'agent_id'>): string {
  return (agent.remote_id || agent.model || agent.target || agent.agent_id || '').trim()
}

/** Child agents of this remote team (siblings when `agent` is itself a child). */
export function remoteMembersOf(
  agent: Agent | undefined,
  agents: Agent[],
): RemoteMemberOption[] {
  if (!agent || agentTypeOf(agent) !== 'remote') return []
  const parentId = agent.parent_id || agent.agent_id
  const framework = (agent.framework || '').toLowerCase()
  const seen = new Set<string>()
  const out: RemoteMemberOption[] = []
  for (const row of agents) {
    if (agentTypeOf(row) !== 'remote') continue
    const rowParent = row.parent_id || ''
    const sameNode = rowParent === parentId
    const sameFrameworkChild =
      !agent.parent_id &&
      !!rowParent &&
      !!framework &&
      (row.framework || '').toLowerCase() === framework
    if (!sameNode && !sameFrameworkChild) continue
    const id = remoteMemberIdOf(row)
    if (!id || seen.has(id)) continue
    seen.add(id)
    out.push({ id, name: row.customName || row.name || id })
  }
  return out
}

export function defaultRemoteMemberId(
  agent: Agent | undefined,
  members: RemoteMemberOption[],
): string {
  if (!agent) return ''
  const own = agent.remote_id || (agent.parent_id ? remoteMemberIdOf(agent) : '')
  if (own && members.some((m) => m.id === own)) return own
  if ((agent.framework || '').toLowerCase() === 'openmausbot') {
    const cos = members.find(
      (m) => isChiefOfStaffRemoteName(m.name) || isChiefOfStaffRemoteName(m.id),
    )
    if (cos) return cos.id
  }
  return members[0]?.id || own || ''
}
