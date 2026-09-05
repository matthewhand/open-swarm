import { Badge, Button, Card } from './DaisyUI'
import {
  resolveOpenInAction,
  teammateTaskRegionLabel,
  type OpenInContext,
  type TeammateTaskEvent,
} from '../lib/teammateTask'

export interface TeammateTaskCardProps {
  event: TeammateTaskEvent
  context: OpenInContext
}

function statusBadgeType(status: string | undefined): 'info' | 'success' | 'neutral' {
  const key = (status || '').trim().toLowerCase()
  if (key === 'running') return 'info'
  if (key === 'done' || key === 'finished') return 'success'
  return 'neutral'
}

/**
 * Thread chrome for a team task whose worker is a configured remote (REQ-84).
 * Open in {Kind} uses the remotes catalog — never a guessed host, never OMB.
 */
export function TeammateTaskCard({ event, context }: TeammateTaskCardProps) {
  const action = resolveOpenInAction(event, context)
  const status = (event.status || '').trim()

  return (
    <Card
      bordered
      compact
      className="os-teammate-task-card bg-base-100 w-full max-w-xl"
      data-testid="teammate-task-card"
      role="region"
      aria-label={teammateTaskRegionLabel(event)}
    >
      <div className="os-teammate-task-card__header flex flex-wrap items-center gap-2">
        {status ? (
          <Badge type={statusBadgeType(status)} size="sm" className="os-teammate-task-card__status">
            {status}
          </Badge>
        ) : null}
      </div>
      {event.title ? (
        <p className="os-teammate-task-card__title font-medium" data-testid="teammate-task-title">
          {event.title}
        </p>
      ) : null}
      <div className="os-teammate-task-card__actions card-actions justify-end mt-2 flex flex-wrap gap-2">
        {action?.kind === 'link' ? (
          <a
            className="btn btn-primary btn-sm"
            href={action.href}
            target={action.target}
            rel={action.target === '_blank' ? 'noopener noreferrer' : undefined}
            data-testid="teammate-task-open"
          >
            {action.label}
          </a>
        ) : null}
        {action?.kind === 'disabled' ? (
          <Button
            type="button"
            size="sm"
            variant="disabled"
            disabled
            className="os-teammate-task-card__open"
            data-testid="teammate-task-open"
            title={action.reason}
            aria-label={action.reason}
          >
            {action.label}
          </Button>
        ) : null}
      </div>
    </Card>
  )
}

export default TeammateTaskCard
