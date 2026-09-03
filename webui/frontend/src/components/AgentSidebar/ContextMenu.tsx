import { useEffect } from 'react'
import type { Agent } from '../../types/agent'

interface ContextMenuProps {
  agent: Agent
  x: number
  y: number
  isChiefOfStaff: boolean
  onClose: () => void
  onRename: (agentId: string, newName: string) => void
  onSetChiefOfStaff: (agentId: string | null) => void
  isFavourite?: boolean
  onToggleFavourite?: () => void
  isHidden?: boolean
  onHide?: (agentId: string) => void
  onUnhide?: (agentId: string) => void
}

export function ContextMenu({
  agent,
  x,
  y,
  isChiefOfStaff,
  onClose,
  onRename,
  onSetChiefOfStaff,
  isFavourite,
  onToggleFavourite,
  isHidden,
  onHide,
  onUnhide,
}: ContextMenuProps) {
  useEffect(() => {
    const close = () => onClose()
    window.addEventListener('click', close)
    window.addEventListener('contextmenu', close)
    return () => {
      window.removeEventListener('click', close)
      window.removeEventListener('contextmenu', close)
    }
  }, [onClose])

  return (
    <div
      role="menu"
      className="fixed z-50 min-w-44 rounded-lg border border-base-300 bg-base-100 py-1 shadow-lg text-sm"
      style={{ left: x, top: y }}
      onClick={(e) => e.stopPropagation()}
    >
      <button
        type="button"
        className="w-full px-3 py-1.5 text-left hover:bg-base-200"
        onClick={() => {
          const next = window.prompt('Rename agent', agent.customName || agent.name)
          if (next && next.trim()) onRename(agent.agent_id, next.trim())
          onClose()
        }}
      >
        Rename
      </button>
      <button
        type="button"
        className="w-full px-3 py-1.5 text-left hover:bg-base-200"
        onClick={() => {
          onSetChiefOfStaff(isChiefOfStaff ? null : agent.agent_id)
          onClose()
        }}
      >
        {isChiefOfStaff ? 'Clear Chief of Staff' : 'Set as Chief of Staff'}
      </button>
      {onToggleFavourite && (
        <button
          type="button"
          className="w-full px-3 py-1.5 text-left hover:bg-base-200"
          onClick={() => {
            onToggleFavourite()
            onClose()
          }}
        >
          {isFavourite ? 'Unpin from focused' : 'Pin to focused'}
        </button>
      )}
      {isHidden && onUnhide ? (
        <button
          type="button"
          className="w-full px-3 py-1.5 text-left hover:bg-base-200"
          onClick={() => {
            onUnhide(agent.agent_id)
            onClose()
          }}
        >
          Unhide
        </button>
      ) : onHide ? (
        <button
          type="button"
          className="w-full px-3 py-1.5 text-left hover:bg-base-200"
          onClick={() => {
            onHide(agent.agent_id)
            onClose()
          }}
        >
          Hide from sidebar
        </button>
      ) : null}
    </div>
  )
}
