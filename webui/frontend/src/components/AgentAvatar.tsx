import { useEffect, useState } from 'react'
import { useAvatarTheme } from '../lib/useAvatarTheme'
import BlobAvatar from './BlobAvatar'

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
  /** Custom face URL. Blank / missing / broken uses the themed default (or bland if selected in settings). */
  src?: string | null
  alt?: string
  size?: AgentAvatarSize
  className?: string
  agentId?: string | null
  active?: boolean
}

export function resolveAgentAvatarSrc(src?: string | null): string {
  const trimmed = typeof src === 'string' ? src.trim() : ''
  return trimmed || DEFAULT_AGENT_AVATAR_SRC
}

export function agentAvatarKind(src?: string | null): 'custom' | 'default' {
  return resolveAgentAvatarSrc(src) === DEFAULT_AGENT_AVATAR_SRC ? 'default' : 'custom'
}

/**
 * Shared agent face for the rail tile, favourites large tiles, and the chat header.
 * Display-only: no click handler. Sizes: rail sm, header/favs lg.
 * Unset or broken avatars resolve to Blobs-with-eyes by default (REQ-155),
 * or bland static circles when opt-in chosen in Settings. Custom faces always win.
 */
export default function AgentAvatar({
  src,
  alt = '',
  size = 'sm',
  className = '',
  agentId,
  active = false,
}: AgentAvatarProps) {
  const [broken, setBroken] = useState(false)
  const theme = useAvatarTheme()

  useEffect(() => {
    setBroken(false)
  }, [src])

  const customSrc = typeof src === 'string' ? src.trim() : ''
  const isCustom = Boolean(customSrc && !broken)

  if (isCustom) {
    return (
      <div
        className={`avatar ${className}`.trim()}
        data-agent-avatar="custom"
        aria-hidden={alt ? undefined : true}
      >
        <div className={`os-agent-avatar os-agent-avatar--${size} rounded-full`}>
          <img
            src={customSrc}
            alt={alt}
            draggable={false}
            data-agent-avatar="custom"
            onError={() => setBroken(true)}
          />
        </div>
      </div>
    )
  }

  // Unset or broken face -> resolve via avatar theme
  if (theme === 'blobs') {
    return (
      <div
        className={`avatar ${className}`.trim()}
        data-agent-avatar="default"
        data-avatar-theme="blobs"
        data-eye-state={active ? 'active' : 'idle'}
        aria-hidden={alt ? undefined : true}
      >
        <BlobAvatar
          agentId={agentId || 'agent'}
          active={active}
          size={size}
          className=""
        />
      </div>
    )
  }

  // Bland static fallback
  return (
    <div
      className={`avatar ${className}`.trim()}
      data-agent-avatar="default"
      aria-hidden={alt ? undefined : true}
    >
      <div className={`os-agent-avatar os-agent-avatar--${size} rounded-full`}>
        <img
          src={DEFAULT_AGENT_AVATAR_SRC}
          alt={alt}
          draggable={false}
          data-agent-avatar="default"
        />
      </div>
    </div>
  )
}
