import { agentMarkIndex } from '../lib/hiddenAgents'
import { useAvatarTheme } from '../lib/useAvatarTheme'
import BlobAvatar from './BlobAvatar'

export interface AgentAvatarProps {
  agentId: string
  /** Selected conversation and/or streaming. */
  active?: boolean
  support?: boolean
  size?: 'sm' | 'md'
  className?: string
}

/**
 * Default theme: today's os-agent-dot. Blobs: deterministic SVG from agent id.
 * Theme switch is localStorage only — never rewrites blueprints.
 */
export default function AgentAvatar({
  agentId,
  active = false,
  support = false,
  size = 'sm',
  className = '',
}: AgentAvatarProps) {
  const theme = useAvatarTheme()

  if (theme === 'blobs') {
    return <BlobAvatar agentId={agentId} active={active} size={size} className={className} />
  }

  return (
    <span
      className={`os-agent-dot ${className}`.trim()}
      data-mark={String(agentMarkIndex(agentId))}
      data-role={support ? 'support' : undefined}
      data-avatar-theme="default"
      aria-hidden="true"
    />
  )
}
