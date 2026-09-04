import { ChevronDown, X } from 'lucide-react'
import { agentMarkColor, agentMarkIndex } from '../lib/hiddenAgents'
import { workingLabel } from '../lib/chatBubble'

export interface WorkingAgentMark {
  id: string
  name: string
}

export function ChatComposerDock({
  workingAgents,
  scrolledUp,
  newMessageCount,
  showNewPill,
  onJumpToBottom,
  onDismissNewCount,
}: {
  workingAgents: WorkingAgentMark[]
  scrolledUp: boolean
  newMessageCount: number
  showNewPill: boolean
  onJumpToBottom: () => void
  onDismissNewCount: () => void
}) {
  if (workingAgents.length === 0 && !scrolledUp) return null

  return (
    <div className="os-chat-dock" data-testid="os-chat-dock">
      <div className="os-chat-dock__workers">
        {workingAgents.length > 0 ? (
          <div className="os-working-avatars" data-testid="os-working-avatars">
            {workingAgents.map((agent) => (
              <span
                key={agent.id}
                className="os-working-avatar"
                data-mark={String(agentMarkIndex(agent.id))}
                style={{ backgroundColor: agentMarkColor(agent.id) }}
                title={workingLabel(agent.name)}
                role="img"
                aria-label={workingLabel(agent.name)}
              />
            ))}
          </div>
        ) : null}
      </div>
      <div className="os-chat-dock__jump">
        {scrolledUp && showNewPill ? (
          <div className="os-new-pill" data-testid="os-new-pill">
            <button
              type="button"
              className="os-new-pill__jump"
              onClick={onJumpToBottom}
              aria-label={`${newMessageCount} ${newMessageCount === 1 ? 'new message' : 'new messages'}`}
            >
              <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
              <span>
                {newMessageCount} {newMessageCount === 1 ? 'new message' : 'new messages'}
              </span>
            </button>
            <button
              type="button"
              className="os-new-pill__dismiss"
              aria-label="Dismiss new message count"
              onClick={onDismissNewCount}
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
        ) : null}
        {scrolledUp && !showNewPill ? (
          <button
            type="button"
            className="os-jump-btn"
            aria-label="Jump to latest messages"
            onClick={onJumpToBottom}
          >
            <ChevronDown className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
          </button>
        ) : null}
      </div>
      <div className="os-chat-dock__spacer" />
    </div>
  )
}
