import { Badge } from './DaisyUI'
import { badgeDaisyType, type EnvBadge } from '../lib/configOwnership'

export default function EnvOverrideBadge({ badge }: { badge?: EnvBadge | null }) {
  if (!badge?.label) return null
  return (
    <span className="inline-flex flex-col items-start gap-0.5">
      <Badge type={badgeDaisyType(badge.kind)} size="sm" className="whitespace-nowrap">
        {badge.label}
      </Badge>
      {badge.helper ? (
        <span className="text-xs text-base-content/60">{badge.helper}</span>
      ) : null}
    </span>
  )
}
