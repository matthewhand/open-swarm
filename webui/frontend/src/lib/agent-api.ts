import { fetchWithAuth } from './api'
import type { 
  AgentInfoResponse, 
  RoutingOptionsResponse, 
  RouteMessageResponse,
  DelegationEvent,
  AgentConversation
} from '../types/agent'

export async function fetchAgents(): Promise<AgentInfoResponse> {
  const response = await fetchWithAuth('/v1/agents/')
  if (!response.ok) {
    throw new Error(`Failed to fetch agents: ${response.statusText}`)
  }
  return response.json()
}

export async function fetchRoutingOptions(): Promise<{ status: string; data: RoutingOptionsResponse }> {
  const response = await fetchWithAuth('/v1/agents/routing-options/')
  if (!response.ok) {
    throw new Error(`Failed to fetch routing options: ${response.statusText}`)
  }
  return response.json()
}

export async function fetchAgentStatus(agentId: string): Promise<any> {
  const response = await fetchWithAuth(`/v1/agents/${agentId}/status/`)
  if (!response.ok) {
    throw new Error(`Failed to fetch status for agent ${agentId}`)
  }
  return response.json()
}

export async function fetchDelegations(): Promise<{ status: string; delegations: DelegationEvent[] }> {
  const response = await fetchWithAuth('/v1/agents/delegations/')
  if (!response.ok) {
    throw new Error(`Failed to fetch delegations: ${response.statusText}`)
  }
  return response.json()
}

export async function routeMessage(params: {
  message: string
  routing_strategy: string
  target_agent?: string | null
  agent_ids?: string[]
  context?: Record<string, any>
  stream?: boolean
  params?: Record<string, string>
}): Promise<RouteMessageResponse> {
  const response = await fetchWithAuth('/v1/agents/route/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  })
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.error || `Routing failed: ${response.statusText}`)
  }
  return response.json()
}

export async function delegateTask(
  targetAgentId: string,
  fromAgent: string,
  message: string,
  context?: Record<string, any>
): Promise<{ status: string; data: DelegationEvent }> {
  const response = await fetchWithAuth(`/v1/agents/${targetAgentId}/delegate/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from_agent: fromAgent,
      message,
      context: context || {}
    })
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Delegation failed: ${response.statusText}`)
  }
  return response.json()
}

export async function fetchConversations(): Promise<{ status: string; conversations: AgentConversation[] }> {
  const response = await fetchWithAuth('/v1/agents/conversations/')
  if (!response.ok) {
    throw new Error(`Failed to fetch conversations: ${response.statusText}`)
  }
  return response.json()
}

export interface CliCatalogEntry {
  name: string
  executable: string
  installed: boolean
  model_flag?: string
  models?: string[]
}

export interface RemoteFrameworkEntry {
  id: string
  name: string
  specialty: string
  description: string
  ollama_available?: boolean
  ollama_launch_dsh?: boolean
  launch_cmd?: string
  default_base_url?: string
}

export async function fetchRemoteCatalog(): Promise<{ status: string; frameworks: RemoteFrameworkEntry[] }> {
  const response = await fetchWithAuth('/v1/agents/remote-catalog/')
  if (!response.ok) {
    throw new Error(`Failed to fetch remote catalog: ${response.statusText}`)
  }
  return response.json()
}

export async function generateAgentQuickstarts(payload: {
  name: string
  system_prompt: string
}): Promise<{ status: string; quickstarts: { key: string; label: string; prompt: string }[] }> {
  const response = await fetchWithAuth('/v1/agents/quickstarts/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.error || `Quickstart generate failed: ${response.statusText}`)
  }
  return data
}

export async function launchRemoteFramework(framework = 'dsh'): Promise<{
  status: string
  ok?: boolean
  launched?: boolean
  via?: string
  ollama?: boolean
  error?: string
  note?: string
  base_url?: string
}> {
  const response = await fetchWithAuth('/v1/agents/remote-launch/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ framework }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.error || `Launch failed: ${response.statusText}`)
  }
  return data
}

export interface LlmProfileEntry {
  name: string
  provider: string
  model: string
  base_url: string
  description: string
}

export async function fetchLlmProfiles(): Promise<{
  status: string
  default: string
  profiles: LlmProfileEntry[]
}> {
  const response = await fetchWithAuth('/v1/agents/llm-profiles/')
  if (!response.ok) {
    throw new Error(`Failed to fetch LLM profiles: ${response.statusText}`)
  }
  return response.json()
}

export async function fetchCliCatalog(): Promise<{ status: string; clis: CliCatalogEntry[] }> {
  const response = await fetchWithAuth('/v1/agents/cli-catalog/')
  if (!response.ok) {
    throw new Error(`Failed to fetch CLI catalog: ${response.statusText}`)
  }
  return response.json()
}

export async function createDesignedAgent(payload: Record<string, unknown>): Promise<{
  status: string
  agent: { agent_id: string; name: string; kind: string }
}> {
  const response = await fetchWithAuth('/v1/agents/design/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.error || `Create agent failed: ${response.statusText}`)
  }
  return data
}

export async function deleteDesignedAgent(agentId: string): Promise<void> {
  const response = await fetchWithAuth(`/v1/agents/design/${encodeURIComponent(agentId)}/`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.error || `Delete agent failed: ${response.statusText}`)
  }
}

export async function startConversation(
  agentId: string,
  message: string
): Promise<{ status: string; conversation: AgentConversation }> {
  const response = await fetchWithAuth('/v1/agents/conversations/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: agentId, message })
  })
  if (!response.ok) {
    throw new Error(`Failed to start conversation: ${response.statusText}`)
  }
  return response.json()
}
