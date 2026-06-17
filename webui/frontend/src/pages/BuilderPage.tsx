import { useState, lazy, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Alert, Badge, LoadingSpinner } from '../components/DaisyUI'
import { Wrench, Cpu, Sparkles, FileCode, FileText, Copy, Check, Download } from 'lucide-react'
import {
  fetchBlueprints,
  fetchBlueprintSource,
  fetchCliAgents,
  type Blueprint,
  type CliAgentsInfo,
} from '../lib/api'

const CodeViewer = lazy(() => import('../components/CodeViewer'))

/** Fallback native-consensus map used until /v1/cli-agents/ loads. */
export const NATIVE_CONSENSUS: Record<string, string[]> = { grok: ['--best-of-n', '{n}'] }

export type ConsensusMode = 'single' | 'self' | 'native' | 'panel'

export function bestOfNFlags(
  cli: string,
  n: number,
  map: Record<string, string[]> = NATIVE_CONSENSUS,
): string[] | null {
  const tmpl = map[cli]
  if (!tmpl) return null
  return tmpl.map((p) => (p === '{n}' ? String(Math.max(2, n)) : p))
}

/** Build a `cli_agents` config entry for a CLI given the chosen consensus mode. */
export function buildAgentConfig(
  cli: string,
  mode: ConsensusMode,
  n: number,
  info: Pick<CliAgentsInfo, 'catalog' | 'native_consensus'> | undefined,
): Record<string, unknown> {
  const base = { ...(info?.catalog?.[cli] ?? { cmd: [cli, '-p', '{prompt}'], parse: 'text' }) }
  const cmd = Array.isArray(base.cmd) ? [...(base.cmd as string[])] : [cli]
  if (mode === 'self') return { ...base, consensus: Math.max(2, n) }
  if (mode === 'panel') return { ...base, consensus: true }
  if (mode === 'native') {
    const flags = bestOfNFlags(cli, n, info?.native_consensus)
    return flags ? { ...base, cmd: [...cmd, ...flags] } : base
  }
  return base // single
}

function AgentConfigBuilder({ info }: { info: CliAgentsInfo | undefined }) {
  const clis = info?.clis ?? ['grok', 'claude', 'gemini', 'opencode']
  const nativeMap = info?.native_consensus ?? NATIVE_CONSENSUS
  const [cli, setCli] = useState('grok')
  const [mode, setMode] = useState<ConsensusMode>('single')
  const [n, setN] = useState(3)
  const [copied, setCopied] = useState(false)

  const nativeSupported = cli in nativeMap
  const effectiveMode = mode === 'native' && !nativeSupported ? 'single' : mode
  const config = { cli_agents: { [cli]: buildAgentConfig(cli, effectiveMode, n, info) } }
  const json = JSON.stringify(config, null, 2)
  const showN = effectiveMode === 'self' || effectiveMode === 'native'

  const copy = async () => {
    try {
      await navigator.clipboard?.writeText(json)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard unavailable */
    }
  }

  const download = () => {
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${cli}.cli_agents.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Card bordered>
      <h2 className="card-title flex items-center gap-2 text-base">
        <Cpu className="h-5 w-5" /> Agent / model setup
      </h2>
      <div className="flex flex-wrap items-end gap-4">
        <label className="form-control">
          <span className="label-text text-xs">CLI / model</span>
          <select className="select select-bordered select-sm" value={cli} aria-label="cli" onChange={(e) => setCli(e.target.value)}>
            {clis.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="form-control">
          <span className="label-text text-xs flex items-center gap-1">
            <Sparkles className="h-3.5 w-3.5 text-primary" /> consensus mode
          </span>
          <select className="select select-bordered select-sm" value={mode} aria-label="consensus mode" onChange={(e) => setMode(e.target.value as ConsensusMode)}>
            <option value="single">single (one inference)</option>
            <option value="self">self-consensus (same persona ×N)</option>
            <option value="native" disabled={!nativeSupported}>
              built-in best-of-N{nativeSupported ? '' : ' (unavailable)'}
            </option>
            <option value="panel">panel (all available CLIs)</option>
          </select>
        </label>
        {showN && (
          <label className="form-control">
            <span className="label-text text-xs">N</span>
            <input type="number" min={2} max={16} value={n} onChange={(e) => setN(Number(e.target.value))} className="input input-bordered input-sm w-20" aria-label="n" />
          </label>
        )}
      </div>

      <div className="mt-3">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wide text-base-content/70">cli_agents config</span>
          <div className="flex gap-1">
            <button type="button" className="btn btn-xs gap-1" onClick={download} aria-label="Download config">
              <Download className="h-3.5 w-3.5" /> Download
            </button>
            <button type="button" className="btn btn-xs gap-1" onClick={copy} aria-label="Copy config">
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        </div>
        <pre
          tabIndex={0}
          role="region"
          aria-label="Generated cli_agents config JSON"
          className="max-h-64 overflow-auto rounded-lg bg-base-300 p-3 text-xs focus:outline focus:outline-2 focus:outline-primary"
        ><code>{json}</code></pre>
      </div>
    </Card>
  )
}

export default function BuilderPage() {
  const { data, isPending, isError } = useQuery({ queryKey: ['blueprints'], queryFn: fetchBlueprints })
  const cliAgents = useQuery({ queryKey: ['cli-agents'], queryFn: fetchCliAgents })

  const blueprints: Blueprint[] = data?.data ?? []
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [openFile, setOpenFile] = useState<string | null>(null)
  const selected = blueprints.find((b) => b.id === selectedId) ?? blueprints[0]

  const source = useQuery({
    queryKey: ['bp-source', selected?.id, openFile],
    queryFn: () => fetchBlueprintSource(selected!.id, openFile ?? undefined),
    enabled: !!selected,
  })

  return (
    <div>
      <h1 className="mb-1 flex items-center gap-2 text-3xl font-bold">
        <Wrench className="h-7 w-7" /> Blueprint Builder
      </h1>
      <p className="mb-6 text-sm text-base-content/70">
        Configure and edit any blueprint — its agents, model setup, and files.
      </p>

      {isPending && <LoadingSpinner />}
      {isError && <Alert type="error">Failed to load blueprints.</Alert>}

      {!isPending && !isError && (
        <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
          {/* Sidebar list on desktop; a compact dropdown on mobile so the config
              and editor aren't buried below a 21-item list. */}
          <Card bordered className="hidden lg:block">
            <h2 className="card-title text-base">Blueprints ({blueprints.length})</h2>
            <ul className="menu menu-sm px-0">
              {blueprints.map((b) => (
                <li key={b.id}>
                  <button
                    className={b.id === selected?.id ? 'active' : ''}
                    aria-current={b.id === selected?.id ? 'true' : undefined}
                    onClick={() => {
                      setSelectedId(b.id)
                      setOpenFile(null)
                    }}
                  >
                    <span className="font-mono text-xs">{b.id}</span>
                  </button>
                </li>
              ))}
            </ul>
          </Card>

          <div className="space-y-4">
            {/* Mobile blueprint picker (the desktop sidebar is hidden < lg). */}
            <label className="form-control lg:hidden">
              <span className="label-text text-xs">Blueprint ({blueprints.length})</span>
              <select
                className="select select-bordered select-sm font-mono"
                aria-label="Select blueprint"
                value={selected?.id ?? ''}
                onChange={(e) => {
                  setSelectedId(e.target.value)
                  setOpenFile(null)
                }}
              >
                {blueprints.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.id}
                  </option>
                ))}
              </select>
            </label>

            <Card bordered>
              <h2 className="card-title flex items-center gap-2 text-base">
                {selected?.id ?? '—'}
              </h2>
              <p className="text-sm text-base-content/70">{selected?.description || 'No description.'}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {(selected?.tags ?? []).map((t) => (
                  <Badge key={t}>{t}</Badge>
                ))}
              </div>
            </Card>

            <AgentConfigBuilder info={cliAgents.data} />

            <Card bordered>
              <h2 className="card-title flex items-center gap-2 text-base">
                <FileCode className="h-5 w-5" /> Source
                {source.data?.selected && (
                  <code className="text-xs font-normal text-base-content/70">{source.data.selected}</code>
                )}
              </h2>
              {source.isPending && <LoadingSpinner size="sm" />}
              {source.isError && <Alert type="warning">Source unavailable for this blueprint.</Alert>}
              {source.data && (
                // Show the file browser only when there's more than one file;
                // otherwise the editor takes the full width (no lonely 1-item list).
                <div className={source.data.files.length > 1 ? 'grid gap-3 md:grid-cols-[180px_1fr]' : ''}>
                  {source.data.files.length > 1 && (
                    <ul className="menu menu-xs rounded-box bg-base-200 px-1" aria-label="Blueprint files">
                      {source.data.files.map((f) => (
                        <li key={f.path}>
                          <button
                            className={f.name === source.data!.selected ? 'active' : ''}
                            aria-current={f.name === source.data!.selected ? 'true' : undefined}
                            onClick={() => setOpenFile(f.name)}
                          >
                            <FileText className="h-3.5 w-3.5" />
                            {f.name}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                  <div className="overflow-hidden rounded-lg border border-base-300">
                    <Suspense fallback={<div className="p-4"><LoadingSpinner size="sm" /></div>}>
                      <CodeViewer value={source.data.content} />
                    </Suspense>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
