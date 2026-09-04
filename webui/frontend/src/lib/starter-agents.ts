import type { Agent } from '../types/agent'

export const STARTER_SUPPORT_ID = 'starter-support'
export const STARTER_CLI_ID = 'starter-cli'
export const STARTER_API_ID = 'starter-api'
export const STARTER_REMOTE_ID = 'starter-remote'

/** Host CLIs the starter CLI agent always offers. */
export const CLI_STARTER_NAMES = ['grok', 'agy'] as const

/** Bump when the visible starter set changes so hide-all re-applies. */
export const STARTER_LAYOUT = 'support-cli-api-remote'

export const STARTER_IDS = [
  STARTER_SUPPORT_ID,
  STARTER_CLI_ID,
  STARTER_API_ID,
  STARTER_REMOTE_ID,
] as const

export function isStarterAgentId(id: string): boolean {
  return (STARTER_IDS as readonly string[]).includes(id)
}

export function isSupportAgent(agent: Pick<Agent, 'agent_id' | 'role'> | undefined): boolean {
  if (!agent) return false
  return agent.role === 'support' || agent.agent_id === STARTER_SUPPORT_ID
}

export function starterAgents(): Agent[] {
  return [
    {
      agent_id: STARTER_SUPPORT_ID,
      name: 'Support',
      specialty: 'Product help, first team, blueprints',
      color: '#f5c542',
      icon: '🛟',
      type: 'specialist',
      group: 'orchestration',
      kind: 'api',
      agent_type: 'api',
      role: 'support',
      description:
        'Onboarding agent. Explains Open Swarm, helps configure inference, and walks you through creating agents, teams, and BlueprintBase Python.',
    },
    {
      agent_id: STARTER_CLI_ID,
      name: 'CLI agent',
      specialty: 'Host CLI (grok or agy)',
      color: '#22c55e',
      icon: '⌨️',
      type: 'specialist',
      group: 'tools',
      kind: 'cli',
      agent_type: 'cli',
      cli: 'grok',
      description: 'One-shot host CLI. Pick grok or agy.',
    },
    {
      agent_id: STARTER_API_ID,
      name: 'API agent',
      specialty: 'LiteLLM + coded blueprint',
      color: '#38bdf8',
      icon: '📦',
      type: 'specialist',
      group: 'specialists',
      kind: 'api',
      agent_type: 'api',
      description: 'OpenAI-compatible chat. Pick a BlueprintBase team to run.',
    },
    {
      agent_id: STARTER_REMOTE_ID,
      name: 'Remote agent',
      specialty: 'Remote team',
      color: '#a78bfa',
      icon: '🛰️',
      type: 'specialist',
      group: 'remote',
      kind: 'remote',
      agent_type: 'remote',
      framework: 'openmausbot',
      description: 'One remote team. Pick Hermes, OpenMausBot, DSH, or another catalog framework.',
    },
  ]
}

export function mergeStarters(agents: Agent[]): Agent[] {
  const byId = new Map(agents.map((agent) => [agent.agent_id, agent]))
  for (const starter of starterAgents()) {
    if (!byId.has(starter.agent_id)) byId.set(starter.agent_id, starter)
  }
  const rest = [...byId.values()].filter((agent) => !isStarterAgentId(agent.agent_id))
  const starters = STARTER_IDS.map((id) => byId.get(id)).filter((agent): agent is Agent => Boolean(agent))
  return [...starters, ...rest]
}

export function hideAllExceptStarters(agentIds: string[]): string[] {
  return agentIds.filter((id) => !isStarterAgentId(id))
}
