import { LifeBuoy, MessageSquare, ScanSearch, Shield } from 'lucide-react'
import type { Blueprint } from '../lib/api'
import { agentMarkIndex } from '../lib/hiddenAgents'
import { roleTone } from '../lib/supportAgents'

type AgentRef = Pick<Blueprint, 'id' | 'role'> | null | undefined

/** Role mark / diamond used in the AGENTS list and the chat header. */
export function AgentMark({
  agent,
  fallbackId = '',
  size = 'sm',
}: {
  agent?: AgentRef
  fallbackId?: string
  size?: 'sm' | 'lg'
}) {
  const ident = agent ?? (fallbackId ? { id: fallbackId, role: null } : null)
  const tone = roleTone(ident)
  const iconClass =
    size === 'lg'
      ? 'os-agent-role-mark h-8 w-8 shrink-0'
      : 'os-agent-role-mark mt-0.5 h-4 w-4 shrink-0'

  if (!ident) {
    return <MessageSquare className={size === 'lg' ? 'h-8 w-8' : 'h-4 w-4'} aria-hidden="true" />
  }
  if (tone === 'support') {
    return <LifeBuoy className={iconClass} aria-hidden="true" />
  }
  if (tone === 'gate') {
    return <Shield className={iconClass} aria-hidden="true" />
  }
  if (tone === 'skeptic') {
    return <ScanSearch className={iconClass} aria-hidden="true" />
  }
  return (
    <span
      className={`os-agent-dot${size === 'lg' ? ' os-agent-dot--lg' : ' mt-1.5'}`}
      data-mark={String(agentMarkIndex(ident.id))}
      aria-hidden="true"
    />
  )
}

export function agentDisplayName(
  agent: Pick<Blueprint, 'id' | 'name'> | null | undefined,
  fallbackId = '',
): string {
  if (agent?.name) return agent.name
  if (agent?.id) return agent.id
  return fallbackId || 'Chat'
}
