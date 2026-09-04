import { memo } from 'react'
import { 
  Bot, 
  Search, 
  FileText, 
  BarChart3, 
  Code, 
  Target, 
  Crown,
} from 'lucide-react'
import type { Agent, AgentStatus, AvatarState, AvatarMotion, AvatarTheme, AvatarEyes } from '../../types/agent'
import { getInitials, getReadableTextColor } from '../../lib/agent-utils'
import { useAgentStore } from '../../lib/agent-store'
import { RobotAvatar } from './RobotAvatar'

export interface AgentAvatarProps {
  agent: Agent
  size?: 40 | 44 | 56 | 32 | 48
  status?: AgentStatus
  state?: AvatarState
  motion?: AvatarMotion
  animated?: boolean
  isChiefOfStaff?: boolean
  theme?: AvatarTheme
  eyes?: AvatarEyes
  className?: string
}

const EMOJI_ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  '🔍': Search,
  '✍️': FileText,
  '📊': BarChart3,
  '💻': Code,
  '🎯': Target,
  '🤖': Bot
}

export const AgentAvatar = memo(function AgentAvatar({
  agent,
  size = 40,
  status = 'idle',
  state,
  motion: _motion,
  animated = true,
  isChiefOfStaff = false,
  theme,
  eyes,
  className = ''
}: AgentAvatarProps) {
  const effectiveState: AvatarState = state || status || 'idle'
  const isAnimated = animated !== false
  const storeTheme = useAgentStore((s) => s.avatarThemeByAgent[agent.agent_id] || s.avatarTheme)
  const storeEyes = useAgentStore((s) => s.avatarEyesByAgent[agent.agent_id] || s.avatarEyes)
  const resolvedTheme = theme || storeTheme
  const resolvedEyes = eyes || storeEyes

  const IconComponent = agent.icon ? EMOJI_ICON_MAP[agent.icon] : null
  const hasEmojiIcon = agent.icon && agent.icon.length <= 2 && !IconComponent
  // Use RobotAvatar if animated; fall back to plain circle for very small sizes
  const useRobot = isAnimated && size >= 32

  if (useRobot) {
    return (
      <RobotAvatar
        color={agent.color || '#6366f1'}
        isChiefOfStaff={isChiefOfStaff || agent.chiefOfStaff}
        status={effectiveState as AgentStatus}
        size={size}
        label={`${agent.customName || agent.name} (${agent.specialty})`}
        trackPointer={size >= 44}
        theme={resolvedTheme}
        eyes={resolvedEyes}
        className={className}
      />
    )
  }

  // Fallback: plain color circle with icon/initials
  const bgColor = agent.color || '#6366f1'
  const textColor = getReadableTextColor(bgColor)
  const sizeClass =
    size === 56 ? 'w-14 h-14 text-xl' :
    size === 44 ? 'w-11 h-11 text-base' :
    size === 48 ? 'w-12 h-12 text-lg' :
    size === 32 ? 'w-8 h-8 text-xs' :
    'w-10 h-10 text-sm'
  const iconSizeClass =
    size === 56 ? 'h-6 w-6' :
    size === 44 ? 'h-5 w-5' :
    size === 32 ? 'h-4 w-4' :
    'h-5 w-5'
  return (
    <div className={`relative inline-flex items-center justify-center flex-shrink-0 ${className}`}>
      <div
        className={`${sizeClass} rounded-full flex items-center justify-center font-bold shadow-sm overflow-hidden select-none`}
        style={{ backgroundColor: bgColor, color: textColor }}
        title={`${agent.customName || agent.name}`}
      >
        {IconComponent ? (
          <IconComponent className={iconSizeClass} />
        ) : hasEmojiIcon ? (
          <span>{agent.icon}</span>
        ) : (
          <span>{getInitials(agent.customName || agent.name)}</span>
        )}
      </div>
      {(isChiefOfStaff || agent.chiefOfStaff) && (
        <span className="absolute -top-1.5 -right-1.5 bg-amber-400 text-amber-950 rounded-full p-0.5 shadow border border-amber-200 z-10">
          <Crown className="w-3.5 h-3.5 fill-amber-900" />
        </span>
      )}
    </div>
  )
})

// Re-export RobotAvatar for direct use
export { RobotAvatar } from './RobotAvatar'
