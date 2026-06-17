import { useState } from 'react'
import { Card } from './DaisyUI'
import { Brain, Gauge, DollarSign, Target } from 'lucide-react'
import type { ConfigOptions, TraitVector } from '../lib/api'
import { TRAITS, resolve, splitCandidate, cliForModel, type Trait } from '../lib/inferenceProfile'
import { ConfigSnippet } from './ConfigSnippet'
import { InfoTip } from './InfoTip'

/** Build the resolution candidate map: a provider candidate per CLI plus a
 *  `<cli>@<model>` candidate for each known model (matched to its CLI by name
 *  prefix), mirroring the backend's candidate_traits. */
export function buildCandidates(
  cliTraits: Record<string, TraitVector>,
  modelTraits: Record<string, TraitVector>,
): Record<string, TraitVector> {
  const out: Record<string, TraitVector> = { ...cliTraits }
  const names = Object.keys(cliTraits)
  for (const [model, traits] of Object.entries(modelTraits)) {
    const cli = cliForModel(model, names)
    if (cli) out[`${cli}@${model}`] = traits
  }
  return out
}

const AXES: { trait: Trait; label: string; icon: typeof Brain }[] = [
  { trait: 'intelligence', label: 'Intelligence', icon: Brain },
  { trait: 'speed', label: 'Speed', icon: Gauge },
  { trait: 'cost', label: 'Cheapness', icon: DollarSign },
]

/** Panel 1: declare what kind of inference a blueprint wants (intelligence /
 *  speed / cost), and live-preview which CLI/model it resolves to. */
export function InferenceProfilePanel({ info }: { info: ConfigOptions | undefined }) {
  const cliTraits = info?.inference.cli_traits ?? {}
  const modelTraits = info?.inference.model_traits ?? {}
  // Which axes the blueprint cares about (unspecified = "don't care").
  const [active, setActive] = useState<Record<Trait, boolean>>({
    intelligence: true,
    speed: false,
    cost: false,
  })
  const [vals, setVals] = useState<Record<Trait, number>>({
    intelligence: 0.9,
    speed: 0.5,
    cost: 0.5,
  })

  const desired: TraitVector = Object.fromEntries(
    TRAITS.filter((t) => active[t]).map((t) => [t, vals[t]]),
  )
  const candidates = buildCandidates(cliTraits, modelTraits)
  const winnerKey = Object.keys(desired).length ? resolve(desired, candidates) : null
  const [cli, model] = winnerKey ? splitCandidate(winnerKey) : [null, null]
  const requestSnippet = JSON.stringify({ params: { profile: desired } }, null, 2)

  return (
    <Card bordered>
      <h2 className="card-title flex items-center gap-2 text-base">
        <Target className="h-5 w-5" /> Inference profile
        <InfoTip text="Declare what kind of inference you want (intelligence / speed / cost). The closest installed CLI/model is chosen automatically." />
      </h2>
      <p className="text-sm text-base-content/70">
        Say what kind of thinking you want — the closest installed CLI/model is chosen for you.
      </p>

      <div className="mt-3 space-y-3">
        {AXES.map(({ trait, label, icon: Icon }) => (
          <div key={trait} className="flex items-center gap-3">
            <label className="flex w-36 items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="checkbox checkbox-sm"
                checked={active[trait]}
                onChange={(e) => setActive({ ...active, [trait]: e.target.checked })}
                aria-label={`Prioritize ${label}`}
              />
              <Icon className="h-4 w-4 opacity-70" />
              {label}
            </label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={vals[trait]}
              disabled={!active[trait]}
              onChange={(e) => setVals({ ...vals, [trait]: Number(e.target.value) })}
              className="range range-primary range-sm flex-1 disabled:opacity-40"
              aria-label={`${label} target`}
            />
            <span className="relative z-10 w-10 shrink-0 bg-base-100 pl-1 text-right font-mono text-xs tabular-nums text-base-content">
              {active[trait] ? vals[trait].toFixed(2) : '—'}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-lg bg-base-200 p-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-base-content/70">
          Resolves to
        </div>
        {winnerKey ? (
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-lg font-bold text-base-content">{cli}</span>
            {model && (
              <span className="badge badge-secondary badge-sm font-mono">model: {model}</span>
            )}
          </div>
        ) : (
          <div className="mt-1 text-sm text-base-content/60">
            Pick at least one axis to resolve a backend.
          </div>
        )}
      </div>

      <ConfigSnippet json={requestSnippet} label="Inference profile request" />
    </Card>
  )
}
