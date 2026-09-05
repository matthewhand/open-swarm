import AgentAvatar from './AgentAvatar'
import AvatarStack from './AvatarStack'
import { personaInitials } from '../lib/personaParse'
import { facesFromDeclaredRoster, type DeclaredTeamRoster } from '../lib/declaredRoster'

export interface PersonaRosterProps {
  roster: DeclaredTeamRoster
  groupId: string
  label?: string
  size?: 'sm' | 'md'
}

/**
 * Declared openai-agents faces for a team (REQ-81). Initials from names.
 * One unparsable blueprint stays a single generic face — no invented names.
 */
export default function PersonaRoster({
  roster,
  groupId,
  label,
  size = 'sm',
}: PersonaRosterProps) {
  const faces = facesFromDeclaredRoster(roster, groupId)
  const count = roster.parsed ? roster.count : 1
  const caption = label || (roster.parsed ? `${count} declared members` : 'Team')

  if (faces.length <= 1) {
    const face = faces[0]
    const name = face?.name || ''
    return (
      <span
        className="os-declared-roster inline-flex items-center gap-1"
        data-testid="declared-roster"
        data-persona-count={String(count)}
        data-roster="declared"
        data-generic={roster.generic ? 'true' : undefined}
        aria-label={caption}
      >
        {name ? (
          <span className="relative inline-flex">
            <AgentAvatar agentId={face?.markId || face?.id || groupId} alt={name} size={size} />
            <span
              className="os-persona-initials pointer-events-none absolute inset-0 flex items-center justify-center text-[0.55rem] font-semibold uppercase text-base-content/90"
              aria-hidden="true"
            >
              {personaInitials(name)}
            </span>
          </span>
        ) : (
          <span
            className="os-persona-generic flex h-5 w-5 items-center justify-center rounded-full bg-base-300 text-[0.55rem] font-semibold text-base-content/70"
            data-testid="generic-persona-face"
            aria-hidden="true"
          >
            ?
          </span>
        )}
      </span>
    )
  }

  return (
    <span
      className="os-declared-roster os-stacked-avatars"
      data-testid="declared-roster"
      data-persona-count={String(count)}
      data-roster="declared"
      data-stack-count={String(faces.length)}
      aria-label={caption}
    >
      <AvatarStack faces={faces} animate={false} />
      <span className="sr-only">
        {roster.personas.map((persona) => persona.name).join(', ')}
      </span>
    </span>
  )
}
