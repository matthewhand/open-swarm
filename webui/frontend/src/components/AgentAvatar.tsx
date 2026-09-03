import defaultAgentAvatarUrl from '../assets/default-agent-avatar.svg'

/** Vite-resolved URL for the original default agent avatar SVG. */
export const DEFAULT_AGENT_AVATAR_SRC = defaultAgentAvatarUrl

export type AgentAvatarSize = 'sm' | 'md' | 'lg' | 'xl'

export interface AgentAvatarProps {
  /** Custom avatar URL. When omitted or blank, the Bert-like default is used. */
  src?: string | null
  alt?: string
  size?: AgentAvatarSize
  className?: string
}

/**
 * Default / fallback agent face.
 *
 * Sidepane uses sm (~28px); chat bubbles md; chat header lg; empty chat xl.
 * Custom `src` wins; everything else is the original cyan pear-blob SVG.
 */
export default function AgentAvatar({
  src,
  alt = '',
  size = 'sm',
  className = '',
}: AgentAvatarProps) {
  const resolved = src && src.trim() ? src.trim() : DEFAULT_AGENT_AVATAR_SRC
  const isDefault = resolved === DEFAULT_AGENT_AVATAR_SRC
  return (
    <img
      src={resolved}
      alt={alt}
      draggable={false}
      data-agent-avatar={isDefault ? 'default' : 'custom'}
      className={`os-agent-avatar os-agent-avatar--${size} ${className}`.trim()}
    />
  )
}
