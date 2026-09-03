import { agentMarkColor, agentMarkIndex } from '../lib/hiddenAgents'
import {
  STACKED_AVATAR_MAX,
  stackedAvatarPlan,
  type AgentSession,
} from '../lib/scaleOutSessions'

export interface StackedAvatarsProps {
  sessions: readonly AgentSession[]
  /** Override the rail cap (tests may render 4 faces). Default 3. */
  maxFaces?: number
  className?: string
}

/**
 * Consolidated hop-style stack: overlapping circular faces, then +N.
 * Every face pulses with the shared motion language; delay is keyed off
 * `startedAt` so they do not lockstep.
 */
export default function StackedAvatars({
  sessions,
  maxFaces = STACKED_AVATAR_MAX,
  className = '',
}: StackedAvatarsProps) {
  const plan = stackedAvatarPlan(sessions, maxFaces)
  if (plan.faces.length === 0) return null

  return (
    <span
      className={`os-stacked-avatars ${className}`.trim()}
      data-face-count={String(plan.faces.length)}
      data-remainder={String(plan.remainder)}
      aria-hidden="true"
    >
      {plan.faces.map((session, index) => (
        <span
          key={session.id}
          className="os-stacked-avatar os-stacked-avatar--stacked os-stacked-avatar--pulse"
          data-testid="os-stacked-avatar"
          data-session-id={session.id}
          data-started-at={String(session.startedAt)}
          data-mark={String(agentMarkIndex(session.id || session.agentId))}
          title={session.title}
          style={{
            backgroundColor: agentMarkColor(session.id || session.agentId),
            animationDelay: `${plan.delaysMs[index] ?? 0}ms`,
          }}
        />
      ))}
      {plan.remainder > 0 ? (
        <span className="os-stacked-remainder" data-testid="os-stacked-remainder">
          +{plan.remainder}
        </span>
      ) : null}
    </span>
  )
}
