import AvatarStack from './AvatarStack'
import {
  sessionToStackFace,
  stackedAvatarPlan,
  type AgentSession,
} from '../lib/scaleOutSessions'
import { STACK_FACE_LIMIT } from '../lib/avatarStack'

export interface StackedAvatarsProps {
  sessions: readonly AgentSession[]
  /** Override the rail cap (tests may render 4 faces). Default 3. */
  maxFaces?: number
  className?: string
}

/**
 * Scale-out session adapter for the shared {@link AvatarStack} widget.
 * Teams/remotes (#398) should import `AvatarStack` directly — do not fork this.
 */
export default function StackedAvatars({
  sessions,
  maxFaces = STACK_FACE_LIMIT,
  className = '',
}: StackedAvatarsProps) {
  const plan = stackedAvatarPlan(sessions, maxFaces)
  return (
    <AvatarStack
      faces={plan.faces.map(sessionToStackFace)}
      remainder={plan.remainder}
      maxFaces={maxFaces}
      className={className}
    />
  )
}
