import type { SkillInfo } from '../lib/skills'
import { skillSourcePath } from '../lib/skills'

export interface SkillChipProps {
  name: string
  raw?: string
  skill?: SkillInfo | null
  missing?: boolean
  onClick?: () => void
}

/** Inline chat affordance for a SKILL.md reference (REQ-212). */
export function SkillChip({ name, raw, skill, missing, onClick }: SkillChipProps) {
  const unloadable = Boolean(missing || skill?.found === false)
  const label = skill?.name || name
  const title = unloadable
    ? skill?.error || `Skill '${name}' not found`
    : skill
      ? `${label} — ${skillSourcePath(skill)}`
      : raw || name

  return (
    <button
      type="button"
      className={`os-skill-chip${unloadable ? ' os-skill-chip--missing' : ''}`}
      data-testid="skill-chip"
      data-skill-name={name}
      data-skill-missing={unloadable ? 'true' : 'false'}
      title={title}
      onClick={(event) => {
        event.preventDefault()
        event.stopPropagation()
        onClick?.()
      }}
    >
      <span className="os-skill-chip__mark" aria-hidden="true">
        {unloadable ? '!' : '#'}
      </span>
      <span className="os-skill-chip__name">{label}</span>
      {unloadable ? <span className="os-skill-chip__state">Missing</span> : null}
    </button>
  )
}
