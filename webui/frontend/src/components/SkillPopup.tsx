import { useEffect, useState, type ReactNode } from 'react'
import { BookOpen, X } from 'lucide-react'
import { Modal } from './DaisyUI'
import { fetchSkill, type SkillRecord } from '../lib/api'
import { renderSafeMarkdown } from '../lib/markdown'
import { skillLookupError, skillSourcePath } from '../lib/skills'

export interface SkillPopupProps {
  name: string | null
  open: boolean
  onClose: () => void
  catalog?: SkillRecord[]
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="text-xs font-semibold uppercase tracking-wide text-base-content/55">{label}</div>
      <div className="text-sm text-base-content">{children}</div>
    </div>
  )
}

/** Dismissible skill card: name, description, source path/id, body preview. */
export function SkillPopup({ name, open, onClose, catalog }: SkillPopupProps) {
  const [skill, setSkill] = useState<SkillRecord | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open || !name) {
      setSkill(null)
      return
    }
    const cached = catalog?.find((row) => row.name === name)
    if (cached) setSkill(cached)
    let cancelled = false
    setLoading(true)
    void fetchSkill(name)
      .then((row) => {
        if (!cancelled) setSkill(row)
      })
      .catch((error: Error) => {
        if (!cancelled) {
          setSkill({
            name,
            id: name,
            description: '',
            assets: [],
            found: false,
            error: error.message || skillLookupError(name),
          })
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, name, catalog])

  const missing = Boolean(!name || skill?.found === false)
  const title = skill?.name || name || 'Skill'
  const source = skill ? skillSourcePath(skill) : name ? `skills/${name}/SKILL.md` : ''
  const body = skill?.instructions || ''
  const error = skill?.error || (name ? skillLookupError(name) : 'No skill selected.')

  return (
    <Modal isOpen={open} onClose={onClose} size="lg" aria-label="Skill">
      <div className="flex items-start justify-between gap-3" data-testid="skill-popup">
        <h3 className="font-bold text-lg">{missing ? 'Skill unavailable' : 'Skill'}</h3>
        <button
          type="button"
          className="btn btn-ghost btn-sm btn-circle"
          aria-label="Close"
          onClick={onClose}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      <div className="mt-3 flex items-start gap-3">
        <span
          className="mt-0.5 inline-flex h-10 w-10 items-center justify-center rounded-box bg-base-200"
          aria-hidden="true"
        >
          <BookOpen className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-base" data-testid="skill-popup-name">
              {title}
            </p>
            <span
              className={`badge badge-sm ${missing ? 'badge-error' : 'badge-ghost'}`}
              data-testid="skill-popup-visibility"
            >
              {missing ? 'Missing' : 'Bundled skill'}
            </span>
          </div>
          {loading ? (
            <p className="text-sm text-base-content/60 mt-1">Loading skill…</p>
          ) : missing ? (
            <p className="text-sm text-error mt-1" data-testid="skill-popup-error">
              {error}
            </p>
          ) : (
            <p className="text-sm text-base-content/70 mt-1" data-testid="skill-popup-summary">
              {skill?.description || 'No description.'}
            </p>
          )}
        </div>
      </div>

      <div className="mt-5 space-y-4">
        <Field label="Name">
          <span data-testid="skill-popup-field-name">{title}</span>
        </Field>
        <Field label="Description">
          <span data-testid="skill-popup-field-description">
            {missing ? error : skill?.description || 'No description.'}
          </span>
        </Field>
        <Field label="Source">
          <code className="text-xs break-all" data-testid="skill-popup-source">
            {source || name || '—'}
          </code>
        </Field>
        <Field label="Instructions">
          {missing ? (
            <p className="text-sm text-base-content/60">No SKILL.md body to preview.</p>
          ) : (
            <div
              data-testid="skill-popup-instructions"
              className="os-skill-preview chat-md max-h-72 overflow-y-auto rounded-box border border-base-300 bg-base-200/40 p-3"
              dangerouslySetInnerHTML={{
                __html: renderSafeMarkdown(body || '_Empty SKILL.md body._'),
              }}
            />
          )}
        </Field>
      </div>
    </Modal>
  )
}
