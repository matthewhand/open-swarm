import { useState } from 'react'
import { Card } from './DaisyUI'
import { Sparkles, Paperclip, Check } from 'lucide-react'
import type { ConfigOptions } from '../lib/api'
import { buildSkillRequest } from '../lib/skills'

/** Panel 3: browse discovered skills and attach one to a cli_agent request. */
export function SkillsPanel({ info }: { info: ConfigOptions | undefined }) {
  const skills = info?.skills ?? []
  const [selected, setSelected] = useState<string | null>(null)
  const request = buildSkillRequest(selected)
  const selectedSkill = skills.find((s) => s.name === selected)

  return (
    <Card bordered>
      <h2 className="card-title flex items-center gap-2 text-base">
        <Sparkles className="h-5 w-5" /> Skills
      </h2>
      <p className="text-sm text-base-content/70">
        Attach a reusable capability — its instructions are prepended and any bundled scripts are
        staged for the CLI.
      </p>

      {skills.length === 0 ? (
        <p className="mt-3 text-sm text-base-content/60">No skills discovered.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {skills.map((s) => {
            const active = selected === s.name
            return (
              <li key={s.name}>
                <button
                  type="button"
                  aria-pressed={active}
                  onClick={() => setSelected(active ? null : s.name)}
                  className={`flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors ${
                    active
                      ? 'border-primary bg-primary/10'
                      : 'border-base-300 hover:border-base-content/30'
                  }`}
                >
                  <span
                    className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                      active ? 'border-primary bg-primary text-primary-content' : 'border-base-content/30'
                    }`}
                    aria-hidden
                  >
                    {active && <Check className="h-3.5 w-3.5" />}
                  </span>
                  <span className="min-w-0">
                    <span className="flex flex-wrap items-center gap-2">
                      <code className="text-sm font-semibold">{s.name}</code>
                      {s.assets.map((a) => (
                        <span key={a} className="badge badge-neutral badge-sm gap-1 font-mono">
                          <Paperclip className="h-3 w-3" /> {a}
                        </span>
                      ))}
                    </span>
                    <span className="mt-0.5 block text-xs text-base-content/70">{s.description}</span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {selectedSkill?.instructions && (
        <details className="mt-3 rounded-lg border border-base-300 bg-base-200">
          <summary className="cursor-pointer px-3 py-2 text-xs font-semibold uppercase tracking-wide text-base-content/70">
            SKILL.md — {selectedSkill.name}
          </summary>
          <pre
            tabIndex={0}
            role="region"
            aria-label={`${selectedSkill.name} SKILL.md instructions`}
            className="max-h-64 overflow-auto whitespace-pre-wrap px-3 pb-3 text-xs text-base-content focus:outline focus:outline-2 focus:outline-primary"
          >
            {selectedSkill.instructions}
          </pre>
        </details>
      )}

      {request && (
        <div className="mt-3">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-base-content/70">
            Request snippet
          </div>
          <pre
            tabIndex={0}
            role="region"
            aria-label="Skill request snippet"
            className="overflow-auto rounded-lg bg-base-300 p-3 text-xs focus:outline focus:outline-2 focus:outline-primary"
          >
            <code>{JSON.stringify(request, null, 2)}</code>
          </pre>
        </div>
      )}
    </Card>
  )
}
