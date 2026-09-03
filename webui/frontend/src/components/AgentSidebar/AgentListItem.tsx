import { memo, type MouseEvent } from 'react'
import type { Agent, AgentStatus, SidebarDensity } from '../../types/agent'
import { OVERSIGHT_ROLES, type OversightRole } from '../../lib/agent-roles'
import { isSupportAgent } from '../../lib/starter-agents'
import { AgentAvatar } from './AgentAvatar'

interface AgentListItemProps {
  agent: Agent
  density: SidebarDensity
  isSelected: boolean
  status: AgentStatus
  unreadCount: number
  isChiefOfStaff: boolean
  heldRoles?: OversightRole[]
  layout?: 'row' | 'tile'
  onClick: () => void
  onContextMenu: (e: MouseEvent) => void
  isDraggable?: boolean
  isDragging?: boolean
  isDragOver?: boolean
  onDragStart?: (e: React.DragEvent<HTMLElement>, agentId: string) => void
  onDragOver?: (e: React.DragEvent<HTMLElement>, agentId: string) => void
  onDragEnter?: (e: React.DragEvent<HTMLElement>, agentId: string) => void
  onDragLeave?: (e: React.DragEvent<HTMLElement>, agentId: string) => void
  onDrop?: (e: React.DragEvent<HTMLElement>, agentId: string) => void
  onDragEnd?: () => void
}

export const AgentListItem = memo(function AgentListItem({
  agent,
  density,
  isSelected,
  status,
  unreadCount,
  isChiefOfStaff,
  heldRoles = [],
  layout = 'row',
  onClick,
  onContextMenu,
  isDraggable,
  isDragging,
  isDragOver,
  onDragStart,
  onDragOver,
  onDragEnter,
  onDragLeave,
  onDrop,
  onDragEnd,
}: AgentListItemProps) {
  const label = agent.customName || agent.name
  const icons = density === 'icons'
  const tile = layout === 'tile'
  const support = isSupportAgent(agent)

  return (
    <div
      draggable={Boolean(isDraggable)}
      onDragStart={(e) => onDragStart?.(e, agent.agent_id)}
      onDragOver={(e) => onDragOver?.(e, agent.agent_id)}
      onDragEnter={(e) => onDragEnter?.(e, agent.agent_id)}
      onDragLeave={(e) => onDragLeave?.(e, agent.agent_id)}
      onDrop={(e) => onDrop?.(e, agent.agent_id)}
      onDragEnd={onDragEnd}
      className={`${isDragging ? 'opacity-40' : ''} ${tile ? 'aspect-square' : ''}`}
    >
      <button
        type="button"
        onClick={onClick}
        onContextMenu={onContextMenu}
        title={label}
        className={
          tile
            ? `relative w-full h-full flex flex-col items-center justify-center gap-0.5 rounded-xl p-1 transition-colors ${
                isSelected ? 'bg-primary/15 text-primary' : 'hover:bg-base-200/80'
              } ${isDragOver ? 'ring-2 ring-primary ring-inset' : ''}`
            : `w-full flex items-center gap-2.5 px-3 py-1.5 text-left transition-colors ${
                isSelected ? 'bg-primary/15 text-primary' : 'hover:bg-base-200/80'
              } ${support ? 'border-l-2 border-warning bg-warning/10' : ''} ${
                isDragOver ? 'ring-1 ring-primary ring-inset' : ''
              } ${icons ? 'justify-center px-0' : ''}`
        }
      >
        <AgentAvatar
          agent={agent}
          size={tile || icons ? 32 : 40}
          status={status}
          isChiefOfStaff={isChiefOfStaff}
        />
        {tile && density !== 'icons' && (
          <span className="w-full text-[10px] font-medium leading-tight truncate text-center px-0.5">
            {label}
          </span>
        )}
        {!tile && !icons && (
          <span className="min-w-0 flex-1">
            <span className="flex items-center gap-1 min-w-0">
              <span className="block text-sm font-semibold truncate">{label}</span>
              {support && (
                <span className="badge badge-xs badge-warning shrink-0 uppercase tracking-wide">
                  Support
                </span>
              )}
            </span>
            <span className="block text-[11px] text-base-content/55 truncate">
              {support
                ? 'Onboarding · teams · blueprints'
                : heldRoles.length
                  ? heldRoles.map((id) => OVERSIGHT_ROLES.find((r) => r.id === id)?.short).join(' · ')
                  : agent.customPurpose || agent.specialty}
            </span>
          </span>
        )}
        {!tile && !icons && unreadCount > 0 && (
          <span className="badge badge-sm badge-primary">{unreadCount}</span>
        )}
        {tile && unreadCount > 0 && (
          <span className="absolute top-0.5 right-0.5 badge badge-xs badge-primary">{unreadCount}</span>
        )}
      </button>
    </div>
  )
})
