import { useEffect, useState } from 'react'

/**
 * Bland circular fallback — not the Bert-like default owned by REQ-6 (#309).
 * Custom `src` wins; a broken image falls back here instead of a broken-icon.
 */
export const DEFAULT_AGENT_AVATAR_SRC =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" role="img" aria-hidden="true">
      <circle cx="20" cy="20" r="20" fill="#2a2a2a"/>
      <circle cx="20" cy="16" r="7" fill="#8a8a8a"/>
      <ellipse cx="20" cy="36" rx="12" ry="10" fill="#8a8a8a"/>
    </svg>`,
  )

export type AgentAvatarSize = 'sm' | 'md' | 'lg' | 'xl'

export interface AgentAvatarProps {
  /** Custom face URL. Blank / missing / broken uses the bland default. */
  src?: string | null
  alt?: string
  size?: AgentAvatarSize
  className?: string
}

export function resolveAgentAvatarSrc(src?: string | null): string {
  const trimmed = typeof src === 'string' ? src.trim() : ''
  return trimmed || DEFAULT_AGENT_AVATAR_SRC
}

export function agentAvatarKind(src?: string | null): 'custom' | 'default' {
  return resolveAgentAvatarSrc(src) === DEFAULT_AGENT_AVATAR_SRC ? 'default' : 'custom'
}

/**
 * Shared agent face for the rail tile and the chat header.
 * Display-only: no click handler. Sizes: rail sm, header lg.
 */
export default function AgentAvatar({
  src,
  alt = '',
  size = 'sm',
  className = '',
}: AgentAvatarProps) {
  const [broken, setBroken] = useState(false)

  useEffect(() => {
    setBroken(false)
  }, [src])

  const resolved = broken ? DEFAULT_AGENT_AVATAR_SRC : resolveAgentAvatarSrc(src)
  const kind = resolved === DEFAULT_AGENT_AVATAR_SRC ? 'default' : 'custom'

  return (
    <div
      className={`avatar ${className}`.trim()}
      data-agent-avatar={kind}
      aria-hidden={alt ? undefined : true}
    >
      <div className={`os-agent-avatar os-agent-avatar--${size} rounded-full`}>
        <img
          src={resolved}
          alt={alt}
          draggable={false}
          onError={() => {
            if (resolved !== DEFAULT_AGENT_AVATAR_SRC) setBroken(true)
          }}
        />
      </div>
    </div>
  )
}
