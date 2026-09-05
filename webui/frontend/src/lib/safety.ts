import type { AgentRole } from './api'

/** Persist Always-allow tool names per agent (REQ-55 v1, no arg fingerprint). */
export const ALWAYS_ALLOW_STORAGE_KEY = 'swarm_always_allow'

export type SwarmChannel = 'api' | 'cli' | 'remote'

export type ToolCallStatus = 'running' | 'allowed' | 'done' | 'denied' | 'error'

export interface ToolCallState {
  id: string
  name: string
  status: ToolCallStatus
  concerned?: boolean
  needsApproval?: boolean
  agentId?: string
}

export function roleDisplayName(role: AgentRole | string): string {
  const key = String(role || '').trim().toLowerCase()
  if (key === 'gate' || key === 'safety' || key === 'tool_gate') return 'Safety'
  if (key === 'support') return 'Support'
  if (key === 'skeptic') return 'Skeptic'
  if (key === 'suggestions' || key === 'suggestion') return 'Suggestions'
  return key
}

export function usesSwarmApproval(channel: SwarmChannel | string | null | undefined): boolean {
  return (channel || 'api').trim().toLowerCase() === 'api'
}

/** Prompt only when Safety is assigned AND flags concern, and the tool is not always-allowed. */
export function shouldPromptForTool(input: {
  channel?: SwarmChannel | string | null
  safetyAssigned: boolean
  concerned: boolean
  alwaysAllowed?: boolean
}): boolean {
  if (!usesSwarmApproval(input.channel)) return false
  if (!input.safetyAssigned) return false
  if (!input.concerned) return false
  if (input.alwaysAllowed) return false
  return true
}

function readStore(): Record<string, string[]> {
  try {
    const raw = window.localStorage.getItem(ALWAYS_ALLOW_STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
    const out: Record<string, string[]> = {}
    for (const [agentId, names] of Object.entries(parsed as Record<string, unknown>)) {
      if (Array.isArray(names)) {
        out[agentId] = names.filter((name): name is string => typeof name === 'string' && name.length > 0)
      }
    }
    return out
  } catch {
    return {}
  }
}

function writeStore(store: Record<string, string[]>): void {
  try {
    window.localStorage.setItem(ALWAYS_ALLOW_STORAGE_KEY, JSON.stringify(store))
  } catch {
    /* persistence is best-effort */
  }
}

export function isToolAlwaysAllowed(agentId: string, toolName: string): boolean {
  if (!agentId || !toolName) return false
  const names = readStore()[agentId] || []
  return names.includes(toolName)
}

export function rememberAlwaysAllow(agentId: string, toolName: string): void {
  if (!agentId || !toolName) return
  const store = readStore()
  const names = new Set(store[agentId] || [])
  names.add(toolName)
  store[agentId] = [...names]
  writeStore(store)
}

export function loadAlwaysAllowedTools(agentId: string): string[] {
  return [...(readStore()[agentId] || [])]
}

export function upsertToolCall(tools: ToolCallState[], next: ToolCallState): ToolCallState[] {
  const index = tools.findIndex((tool) => tool.id === next.id)
  if (index === -1) return [...tools, next]
  const copy = [...tools]
  copy[index] = { ...copy[index], ...next }
  return copy
}
