import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Alert, Badge, LoadingSpinner } from '../components/DaisyUI'
import { Wrench, Cpu, Sparkles, FileCode, FolderTree } from 'lucide-react'
import { fetchBlueprints, type Blueprint } from '../lib/api'

/**
 * Which CLIs have a built-in "best-of-N" consensus mode. Mirrors the backend
 * `swarm.core.cli_catalog.NATIVE_CONSENSUS` (exposed by `cli-agents --json`); a
 * `/v1/cli-agents/` endpoint will replace this hard-coded map.
 */
export const NATIVE_CONSENSUS: Record<string, string[]> = {
  grok: ['--best-of-n', '{n}'],
}

const CLI_CHOICES = ['grok', 'claude', 'gemini', 'opencode'] as const

/** Resolve the argv a "best-of-N" toggle would append for a CLI, or null. */
export function bestOfNFlags(cli: string, n: number): string[] | null {
  const tmpl = NATIVE_CONSENSUS[cli]
  if (!tmpl) return null
  return tmpl.map((p) => (p === '{n}' ? String(Math.max(2, n)) : p))
}

function BestOfNToggle({ cli }: { cli: string }) {
  const supported = cli in NATIVE_CONSENSUS
  const [on, setOn] = useState(false)
  const [n, setN] = useState(3)
  const flags = on && supported ? bestOfNFlags(cli, n) : null

  return (
    <div className="mt-3 rounded-lg border border-base-300 p-3">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-sm font-medium">
          <Sparkles className="h-4 w-4 text-primary" />
          Built-in consensus (best-of-N)
        </span>
        <input
          type="checkbox"
          className="toggle toggle-primary toggle-sm"
          aria-label="Enable built-in consensus"
          disabled={!supported}
          checked={on && supported}
          onChange={(e) => setOn(e.target.checked)}
        />
      </div>
      {!supported ? (
        <p className="mt-1 text-xs text-gray-500">
          <code>{cli}</code> has no built-in consensus mode — use framework consensus instead.
        </p>
      ) : (
        <div className="mt-2 flex items-center gap-3">
          <label className="text-xs text-gray-500">candidates (N)</label>
          <input
            type="number"
            min={2}
            max={16}
            value={n}
            disabled={!on}
            onChange={(e) => setN(Number(e.target.value))}
            className="input input-bordered input-xs w-16"
            aria-label="best-of-n count"
          />
          <code className="text-xs text-gray-500">
            {flags ? flags.join(' ') : '(off)'}
          </code>
        </div>
      )}
    </div>
  )
}

export default function BuilderPage() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
  })
  const blueprints: Blueprint[] = data?.data ?? []
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [cli, setCli] = useState<string>('grok')
  const selected = blueprints.find((b) => b.id === selectedId) ?? blueprints[0]

  return (
    <div>
      <h1 className="mb-1 flex items-center gap-2 text-3xl font-bold">
        <Wrench className="h-7 w-7" /> Blueprint Builder
      </h1>
      <p className="mb-6 text-sm text-gray-500">
        Configure and edit any blueprint — its agents, model setup, and files.
      </p>

      {isPending && <LoadingSpinner />}
      {isError && <Alert type="error">Failed to load blueprints.</Alert>}

      {!isPending && !isError && (
        <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
          {/* Blueprint list */}
          <Card bordered>
            <h2 className="card-title text-base">Blueprints ({blueprints.length})</h2>
            <ul className="menu menu-sm px-0">
              {blueprints.map((b) => (
                <li key={b.id}>
                  <button
                    className={b.id === selected?.id ? 'active' : ''}
                    onClick={() => setSelectedId(b.id)}
                  >
                    {b.name || b.id}
                  </button>
                </li>
              ))}
            </ul>
          </Card>

          {/* Selected blueprint config */}
          <div className="space-y-4">
            <Card bordered>
              <h2 className="card-title flex items-center gap-2 text-base">
                <Cpu className="h-5 w-5" /> {selected?.name || selected?.id || '—'}
              </h2>
              <p className="text-sm text-gray-500">{selected?.description || 'No description.'}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {(selected?.tags ?? []).map((t) => (
                  <Badge key={t}>{t}</Badge>
                ))}
              </div>
            </Card>

            <Card bordered>
              <h2 className="card-title text-base">Agent / model setup</h2>
              <label className="form-control max-w-xs">
                <span className="label-text text-xs">CLI / model</span>
                <select
                  className="select select-bordered select-sm"
                  value={cli}
                  aria-label="cli"
                  onChange={(e) => setCli(e.target.value)}
                >
                  {CLI_CHOICES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>
              <BestOfNToggle cli={cli} />
            </Card>

            <Card bordered>
              <h2 className="card-title flex items-center gap-2 text-base">
                <FileCode className="h-5 w-5" /> Code <span className="text-xs text-gray-400">(coming next)</span>
              </h2>
              <p className="text-sm text-gray-500">
                <FolderTree className="mr-1 inline h-4 w-4" />
                A CodeMirror editor for the primary blueprint file + a file browser for auxiliary
                files lands in the next increment.
              </p>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
