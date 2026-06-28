import { useMemo, useState } from 'react'
import { Card } from './DaisyUI'
import { Wrench, ShieldCheck, KeyRound, Check, AlertTriangle } from 'lucide-react'
import type { ConfigOptions } from '../lib/api'
import {
  resolveCapabilities,
  buildToolsConfig,
  type Level,
  type McpServerInfo,
} from '../lib/toolCapabilities'
import { ConfigSnippet } from './ConfigSnippet'
import { InfoTip } from './InfoTip'

const LEVELS: (Level | 'off')[] = ['off', 'optional', 'mandatory']

/** Panel 2: declare abstract tool capabilities (mandatory/optional) and pick MCP
 *  providers, with non-auth servers preferred and surfaced first. */
export function ToolCapabilitiesPanel({ info }: { info: ConfigOptions | undefined }) {
  const capabilities = info?.tools.capabilities ?? []
  // non-auth servers first so they're the obvious default.
  const sortedCatalog = useMemo(() => {
    const catalog: McpServerInfo[] = info?.tools.mcp_catalog ?? []
    return [...catalog].sort(
      (a, b) => Number(a.needs_auth) - Number(b.needs_auth) || a.name.localeCompare(b.name),
    )
  }, [info?.tools.mcp_catalog])

  const [reqs, setReqs] = useState<Record<string, Level>>({})
  const [chosen, setChosen] = useState<Set<string>>(new Set())

  const chosenServers = sortedCatalog.filter((s) => chosen.has(s.name))
  const res = resolveCapabilities(reqs, chosenServers)
  const config = buildToolsConfig(reqs, chosenServers)
  const json = JSON.stringify(config, null, 2)

  const setLevel = (cap: string, level: Level | 'off') => {
    setReqs((prev) => {
      const next = { ...prev }
      if (level === 'off') delete next[cap]
      else next[cap] = level
      return next
    })
  }
  const toggleServer = (name: string) =>
    setChosen((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })

  return (
    <Card bordered>
      <h2 className="card-title flex items-center gap-2 text-base">
        <Wrench className="h-5 w-5" /> Tool capabilities
        <InfoTip text="Ask for an abstract capability (e.g. web_search, browser). A non-auth MCP server is preferred so it runs with no API key." />
      </h2>
      <p className="text-sm text-base-content/70">
        Ask for a capability; a non-auth MCP server is preferred so it runs with no API key.
      </p>

      {/* Capability requirements */}
      <div className="mt-3 space-y-2">
        {capabilities.map((cap) => {
          const level = reqs[cap] ?? 'off'
          return (
            <div key={cap} className="flex items-center justify-between gap-2">
              <code className="text-sm">{cap}</code>
              <div className="join" role="group" aria-label={`${cap} requirement`}>
                {LEVELS.map((l) => (
                  <button
                    key={l}
                    type="button"
                    aria-pressed={level === l}
                    onClick={() => setLevel(cap, l)}
                    className={`btn btn-xs join-item ${level === l ? 'btn-primary' : 'btn-ghost'}`}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* MCP servers (non-auth first) */}
      <div className="mt-4">
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-base-content/70">
          MCP servers
        </div>
        <ul className="space-y-1">
          {sortedCatalog.map((s) => (
            <li key={s.name}>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  className="checkbox checkbox-sm"
                  checked={chosen.has(s.name)}
                  onChange={() => toggleServer(s.name)}
                  aria-label={`Add ${s.name}`}
                />
                <span className="font-mono">{s.name}</span>
                {s.needs_auth ? (
                  <span className="badge badge-warning badge-sm gap-1">
                    <KeyRound className="h-3 w-3" /> needs {s.auth_env.join(', ')}
                  </span>
                ) : (
                  <span className="badge badge-success badge-sm gap-1">
                    <ShieldCheck className="h-3 w-3" /> no key
                  </span>
                )}
                <span className="text-xs text-base-content/60">{s.provides.join(', ')}</span>
              </label>
            </li>
          ))}
        </ul>
      </div>

      {/* Resolution preview */}
      {Object.keys(reqs).length > 0 && (
        <div className="mt-4 rounded-lg bg-base-200 p-3 text-sm">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-base-content/70">
            Resolves to
          </div>
          <ul className="space-y-0.5">
            {Object.entries(reqs).map(([cap, level]) => {
              const server = res.satisfied[cap]
              const missing = res.missingMandatory.includes(cap)
              return (
                <li key={cap} className="flex items-center gap-2">
                  <code className="text-xs">{cap}</code>
                  <span aria-hidden>→</span>
                  {server ? (
                    <span className="flex items-center gap-1 text-success">
                      <Check className="h-3.5 w-3.5" /> {server}
                    </span>
                  ) : missing ? (
                    <span className="flex items-center gap-1 text-error">
                      <AlertTriangle className="h-3.5 w-3.5" /> no provider (mandatory)
                    </span>
                  ) : (
                    <span className="text-base-content/60">skipped (optional, {level})</span>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      )}

      <ConfigSnippet json={json} label="Tool capabilities config" />
    </Card>
  )
}
