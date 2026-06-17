import { useEffect, useState } from 'react'
import { Card } from './DaisyUI'
import { SlidersHorizontal, Plus, Trash2 } from 'lucide-react'
import type { ConfigOptions, TraitVector } from '../lib/api'
import {
  TRAITS,
  buildTraitsConfig,
  candidatesFromEdits,
  resolve,
  splitCandidate,
  type ModelRow,
  type Trait,
} from '../lib/inferenceProfile'
import { ConfigSnippet } from './ConfigSnippet'

const round2 = (v: number) => Math.round(v * 100) / 100

/** Per-model trait editor: tune each CLI's capability traits and add per-model
 *  overrides, then emit a cli_agents config (traits + models blocks). */
export function TraitEditorPanel({ info }: { info: ConfigOptions | undefined }) {
  const [cliTraits, setCliTraits] = useState<Record<string, TraitVector>>({})
  const [rows, setRows] = useState<ModelRow[]>([])

  // Seed editable state when the config options load.
  useEffect(() => {
    if (!info) return
    setCliTraits(structuredClone(info.inference.cli_traits))
    const seeded: ModelRow[] = Object.entries(info.inference.model_traits).map(([model, traits]) => ({
      cli: Object.keys(info.inference.cli_traits).find((c) => model.startsWith(c)) ?? Object.keys(info.inference.cli_traits)[0] ?? '',
      model,
      traits: { ...traits },
    }))
    setRows(seeded)
  }, [info])

  const clis = Object.keys(cliTraits)
  const config = buildTraitsConfig(cliTraits, rows)
  // Quick sanity: where would "deep reasoning" resolve given current edits?
  const sample = resolve({ intelligence: 1 }, candidatesFromEdits(cliTraits, rows))
  const [sampleCli, sampleModel] = sample ? splitCandidate(sample) : [null, null]

  const setCli = (cli: string, t: Trait, v: number) =>
    setCliTraits((prev) => ({ ...prev, [cli]: { ...prev[cli], [t]: round2(v) } }))
  const setRow = (i: number, patch: Partial<ModelRow>) =>
    setRows((prev) => prev.map((r, j) => (j === i ? { ...r, ...patch } : r)))
  const setRowTrait = (i: number, t: Trait, v: number) =>
    setRows((prev) => prev.map((r, j) => (j === i ? { ...r, traits: { ...r.traits, [t]: round2(v) } } : r)))

  const num = (value: number, onChange: (v: number) => void, label: string) => (
    <input
      type="number"
      min={0}
      max={1}
      step={0.05}
      value={value}
      aria-label={label}
      onChange={(e) => onChange(Number(e.target.value))}
      className="input input-bordered input-xs w-16 text-base-content"
    />
  )

  return (
    <Card bordered>
      <h2 className="card-title flex items-center gap-2 text-base">
        <SlidersHorizontal className="h-5 w-5" /> Tune backend traits
      </h2>
      <p className="text-sm text-base-content/70">
        Edit each CLI's capability traits and add per-model overrides; emits a <code>cli_agents</code> config.
      </p>

      {/* Per-provider traits */}
      <div className="mt-3 overflow-x-auto">
        <table className="table table-xs">
          <thead>
            <tr>
              <th>CLI</th>
              {TRAITS.map((t) => (
                <th key={t} className="capitalize">{t}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {clis.map((cli) => (
              <tr key={cli}>
                <td className="font-mono">{cli}</td>
                {TRAITS.map((t) => (
                  <td key={t}>{num(cliTraits[cli]?.[t] ?? 0.5, (v) => setCli(cli, t, v), `${cli} ${t}`)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Per-model overrides */}
      <div className="mt-3">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wide text-base-content/70">
            Per-model overrides
          </span>
          <button
            type="button"
            className="btn btn-xs gap-1"
            onClick={() => setRows((p) => [...p, { cli: clis[0] ?? '', model: '', traits: { intelligence: 0.5, speed: 0.5, cost: 0.5 } }])}
          >
            <Plus className="h-3.5 w-3.5" /> add model
          </button>
        </div>
        <ul className="space-y-2">
          {rows.map((r, i) => (
            <li key={i} className="flex flex-wrap items-center gap-2">
              <select
                className="select select-bordered select-xs"
                value={r.cli}
                aria-label={`model ${i} cli`}
                onChange={(e) => setRow(i, { cli: e.target.value })}
              >
                {clis.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              <input
                type="text"
                className="input input-bordered input-xs w-44 font-mono"
                placeholder="model id"
                value={r.model}
                aria-label={`model ${i} id`}
                onChange={(e) => setRow(i, { model: e.target.value })}
              />
              {TRAITS.map((t) => num(r.traits[t] ?? 0.5, (v) => setRowTrait(i, t, v), `model ${i} ${t}`))}
              <button
                type="button"
                className="btn btn-ghost btn-xs"
                aria-label={`remove model ${i}`}
                onClick={() => setRows((p) => p.filter((_, j) => j !== i))}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-3 rounded-lg bg-base-200 p-2 text-xs text-base-content/80">
        Sample: <code>{'{intelligence: 1}'}</code> →{' '}
        <span className="font-semibold text-base-content">{sampleCli ?? '—'}</span>
        {sampleModel && <span className="font-mono"> @{sampleModel}</span>}
      </div>

      <ConfigSnippet json={JSON.stringify(config, null, 2)} label="cli_agents traits config" />
    </Card>
  )
}
