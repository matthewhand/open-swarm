import AgentAvatar from './AgentAvatar'
import { Badge, Button, Card } from './DaisyUI'
import {
  formatPrFileStats,
  isGithubPrUrl,
  isSameOpenerChat,
  type PrOpenedEvent,
  type PrOpenedOpener,
} from '../lib/prOpened'

export interface PrOpenedCardProps {
  event: PrOpenedEvent
  currentAgentId?: string
  currentConversationId?: string
  openerName?: string
  openerAvatarSrc?: string | null
  onJumpToOpener?: (opener: PrOpenedOpener) => void
}

/**
 * Thread chrome for a structured PR-opened tool result (REQ-71).
 * Always View PR when the URL is a real GitHub pull. Jump to the opener
 * only when that agent/thread is not the one already on screen.
 */
export function PrOpenedCard({
  event,
  currentAgentId,
  currentConversationId,
  openerName,
  openerAvatarSrc,
  onJumpToOpener,
}: PrOpenedCardProps) {
  const viewUrl = isGithubPrUrl(event.url) ? event.url : undefined
  const stats = formatPrFileStats(event)
  const showJump =
    !isSameOpenerChat(event.opener, {
      agentId: currentAgentId,
      conversationId: currentConversationId,
    }) && Boolean(event.opener?.agentId)
  const jumpLabel = (openerName || event.opener?.name || event.opener?.agentId || '').trim()

  return (
    <Card
      bordered
      compact
      className="os-pr-opened-card bg-base-100 w-full max-w-xl"
      data-testid="pr-opened-card"
      role="region"
      aria-label={event.title ? `Pull request ${event.title}` : 'Pull request opened'}
    >
      <div className="os-pr-opened-card__header flex flex-wrap items-center gap-2">
        {event.status ? (
          <Badge type="success" size="sm" className="os-pr-opened-card__status">
            {event.status}
          </Badge>
        ) : null}
        {typeof event.number === 'number' ? (
          <span className="os-pr-opened-card__number text-xs opacity-70" data-testid="pr-opened-number">
            PR #{event.number}
          </span>
        ) : null}
        {event.branch ? (
          <span className="os-pr-opened-card__branch font-mono text-xs opacity-70" data-testid="pr-opened-branch">
            {event.branch}
          </span>
        ) : null}
        {stats ? (
          <span className="os-pr-opened-card__stats font-mono text-xs" data-testid="pr-opened-stats">
            <span className="text-success">{stats.split(' ')[0]}</span>
            {stats.includes(' ') ? (
              <span className="text-error">{` ${stats.split(' ').slice(1).join(' ')}`}</span>
            ) : null}
          </span>
        ) : null}
      </div>
      {event.title ? (
        <p className="os-pr-opened-card__title font-medium" data-testid="pr-opened-title">
          {event.title}
        </p>
      ) : null}
      <div className="os-pr-opened-card__actions card-actions justify-end mt-2 flex flex-wrap gap-2">
        {viewUrl ? (
          <a
            className="btn btn-primary btn-sm"
            href={viewUrl}
            target="_blank"
            rel="noopener noreferrer"
            data-testid="pr-opened-view"
          >
            View PR
          </a>
        ) : null}
        {showJump && event.opener ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="os-pr-opened-card__jump gap-2"
            data-testid="pr-opened-jump"
            aria-label={jumpLabel}
            onClick={() => onJumpToOpener?.(event.opener!)}
          >
            <AgentAvatar
              agentId={event.opener.agentId}
              src={openerAvatarSrc}
              alt=""
              size="xs"
            />
            <span>{jumpLabel}</span>
          </Button>
        ) : null}
      </div>
    </Card>
  )
}

export default PrOpenedCard
