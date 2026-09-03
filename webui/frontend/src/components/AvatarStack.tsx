import { agentMarkColor, agentMarkIndex } from '../lib/hiddenAgents'
import {
  earliestStartedAt,
  isAvatarStack,
  stackAnimationDelayStyle,
  type StackFace,
} from '../lib/avatarStack'

export type { StackFace }

export interface AvatarStackProps {
  faces: StackFace[]
  remainder?: number
  /** Team/remote stacks animate every face (REQ-68 addendum). */
  animate?: boolean
  label?: string
}

/**
 * Shared stacked-avatar widget for #394 (scale-out agent) and #398 (team/remote).
 * Max 3 faces + remainder. Do not fork this in the #394 PR — import it.
 */
export default function AvatarStack({
  faces,
  remainder = 0,
  animate = true,
  label,
}: AvatarStackProps) {
  const stacked = isAvatarStack(faces.length, remainder)
  const earliest = earliestStartedAt(faces)
  return (
    <span
      className={`os-avatar-stack shrink-0 ${stacked ? 'os-avatar-stack--stacked' : ''}`}
      data-avatar-stack={stacked ? 'true' : 'false'}
      data-stack-count={String(faces.length)}
      data-remainder={String(remainder)}
      aria-hidden={label ? undefined : true}
      aria-label={label}
    >
      {faces.map((face) => {
        const delay = stackAnimationDelayStyle(face.startedAt, earliest)
        const working = animate || face.working
        return (
          <span
            key={face.id}
            className={`os-avatar-stack__face ${working ? 'os-avatar-stack__face--working' : ''}`}
            data-face-id={face.id}
            data-started-at={String(face.startedAt)}
            data-working={working ? 'true' : undefined}
            data-mark={String(agentMarkIndex(face.id))}
            data-role={face.role}
            title={face.name}
            style={{
              backgroundColor: agentMarkColor(face.id),
              ...(working ? delay : {}),
            }}
          />
        )
      })}
      {remainder > 0 ? (
        <span className="os-avatar-stack__remainder" data-remainder-count={String(remainder)}>
          +{remainder}
        </span>
      ) : null}
    </span>
  )
}
