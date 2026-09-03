import { useEffect, useId, useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, FileCode2, Plus, Server } from 'lucide-react'
import { Alert, Button, Input, Modal, Select, useToast } from './DaisyUI'
import {
  fetchBlueprintSource,
  fetchModels,
  fetchRemotes,
  operateRemote,
  persistRemote,
  probeRemoteHealth,
  type BlueprintSource,
  type RemoteConnection,
} from '../lib/api'
import {
  agentRole,
  fallbackBlueprintSource,
  isExampleRole,
  runtimeModulesFor,
} from '../lib/agentRoles'
import { PYTHON_CODE_CLASS, highlightPython } from '../lib/highlightPython'
import {
  RETENTION_MODES,
  RETENTION_MODE_LABELS,
  detectedHostname,
  loadHostnameOverride,
  loadRetentionMode,
  saveHostnameOverride,
  saveRetentionMode,
  type RetentionMode,
} from '../lib/settingsPrefs'
import { agentLabel } from '../lib/supportAgent'

/** Window event so the rail hover-edit, command palette, and tests can open the sheet. */
export const OPEN_SETTINGS_EVENT = 'swarm:open-settings'

export type SettingsSection =
  | 'blueprint'
  | 'remotes-add'
  | 'remotes-hermes'
  | 'remotes-omb'
  | 'remotes-rakazo'
  | 'remotes-herdr'
  | 'retention'
  | 'hostname'
  | 'llm-profiles'

export interface OpenSettingsDetail {
  section?: SettingsSection
  blueprintId?: string
}

export function openSettingsSheet(detail?: OpenSettingsDetail): void {
  window.dispatchEvent(new CustomEvent<OpenSettingsDetail>(OPEN_SETTINGS_EVENT, { detail }))
}

const REMOTE_PANES = [
  { id: 'remotes-hermes' as const, label: 'Hermes' },
  { id: 'remotes-omb' as const, label: 'OMB' },
  { id: 'remotes-rakazo' as const, label: 'Rakazo' },
]

const REMOTES_QUERY_KEY = ['settings-remotes'] as const

function isRemoteSection(section: SettingsSection): boolean {
  return section.startsWith('remotes-')
}

export interface SettingsSheetProps {
  isOpen: boolean
  onClose: () => void
  blueprintId?: string | null
}

/**
 * Right-docked DaisyUI settings sheet (REQ-19 + REQ-25).
 *
 * Opens as `modal` + `modal-end` over the SPA (not a top-nav eject to Django).
 * Gear opens Remotes / Retention / Hostname / LLM profiles. Hover-edit on a
 * roled agent selects the Blueprint editor for that agent's blueprint id —
 * not the Teams drop-zone roster. Django `/settings/` stays the operator dump.
 */
export default function SettingsSheet({ isOpen, onClose, blueprintId }: SettingsSheetProps) {
  const { success } = useToast()
  const [section, setSection] = useState<SettingsSection>('retention')
  const [remotesOpen, setRemotesOpen] = useState(true)
  const [hostname, setHostname] = useState(() => loadHostnameOverride())
  const [retention, setRetention] = useState<RetentionMode>(() => loadRetentionMode())
  const remotesQuery = useQuery({
    queryKey: REMOTES_QUERY_KEY,
    queryFn: async () => {
      if (typeof fetch !== 'function') {
        return { object: 'list' as const, data: [], kinds: [] }
      }
      return fetchRemotes()
    },
    enabled: isOpen,
    retry: false,
  })
  const herdrRemote = useMemo(
    () => (remotesQuery.data?.data ?? []).find((row) => row.id === 'herdr'),
    [remotesQuery.data],
  )

  useEffect(() => {
    if (!isOpen) return
    setHostname(loadHostnameOverride())
    setRetention(loadRetentionMode())
    if (blueprintId) {
      setSection('blueprint')
    } else {
      setSection((current) => (current === 'blueprint' ? 'retention' : current))
    }
  }, [isOpen, blueprintId])

  const handleSaveHostname = (event: FormEvent) => {
    event.preventDefault()
    saveHostnameOverride(hostname)
    setHostname(loadHostnameOverride())
    success('Hostname saved', 'Override stored in this browser.')
  }

  const handleSaveRetention = (event: FormEvent) => {
    event.preventDefault()
    saveRetentionMode(retention)
    success('Retention saved', `${RETENTION_MODE_LABELS[retention]} mode stored in this browser.`)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Settings"
      placement="end"
      size="sheet"
      className="flex min-h-0 flex-col"
    >
      <div className="flex min-h-[24rem] flex-1 flex-col gap-0 overflow-hidden rounded-box border border-base-300 md:flex-row">
        <nav aria-label="Settings sections" className="w-full shrink-0 border-b border-base-300 bg-base-200 md:w-52 md:border-b-0 md:border-r">
          <ul className="menu menu-md w-full rounded-none p-2">
            <li>
              <button
                type="button"
                className={section === 'blueprint' ? 'menu-active' : undefined}
                aria-current={section === 'blueprint' ? 'page' : undefined}
                onClick={() => setSection('blueprint')}
              >
                Blueprint
              </button>
            </li>
            <li>
              <button
                type="button"
                className={`menu-dropdown-toggle ${remotesOpen ? 'menu-dropdown-show' : ''}`}
                aria-expanded={remotesOpen}
                onClick={() => setRemotesOpen((open) => !open)}
              >
                Remotes
              </button>
              <ul className={`menu-dropdown ${remotesOpen ? 'menu-dropdown-show' : ''}`}>
                {REMOTE_PANES.map((remote) => (
                  <li key={remote.id}>
                    <button
                      type="button"
                      className={section === remote.id ? 'menu-active' : undefined}
                      aria-current={section === remote.id ? 'page' : undefined}
                      onClick={() => setSection(remote.id)}
                    >
                      {remote.label}
                    </button>
                  </li>
                ))}
                {herdrRemote ? (
                  <li>
                    <button
                      type="button"
                      className={section === 'remotes-herdr' ? 'menu-active' : undefined}
                      aria-current={section === 'remotes-herdr' ? 'page' : undefined}
                      onClick={() => setSection('remotes-herdr')}
                    >
                      Herdr
                    </button>
                  </li>
                ) : null}
                <li>
                  <button
                    type="button"
                    className={section === 'remotes-add' ? 'menu-active' : undefined}
                    aria-current={section === 'remotes-add' ? 'page' : undefined}
                    onClick={() => setSection('remotes-add')}
                  >
                    + Add remote
                  </button>
                </li>
              </ul>
            </li>
            <li>
              <button
                type="button"
                className={section === 'retention' ? 'menu-active' : undefined}
                aria-current={section === 'retention' ? 'page' : undefined}
                onClick={() => setSection('retention')}
              >
                Retention
              </button>
            </li>
            <li>
              <button
                type="button"
                className={section === 'hostname' ? 'menu-active' : undefined}
                aria-current={section === 'hostname' ? 'page' : undefined}
                onClick={() => setSection('hostname')}
              >
                Hostname
              </button>
            </li>
            <li>
              <button
                type="button"
                className={section === 'llm-profiles' ? 'menu-active' : undefined}
                aria-current={section === 'llm-profiles' ? 'page' : undefined}
                onClick={() => setSection('llm-profiles')}
              >
                LLM profiles
              </button>
            </li>
          </ul>
        </nav>

        <div className="min-w-0 flex-1 overflow-y-auto bg-base-100 p-4 sm:p-5">
          {section === 'blueprint' && (
            <BlueprintEditorPane blueprintId={blueprintId || ''} />
          )}
          {isRemoteSection(section) && (
            <RemotePane
              section={section}
              herdr={herdrRemote}
              onAddedHerdr={() => setSection('remotes-herdr')}
            />
          )}
          {section === 'retention' && (
            <RetentionPane
              value={retention}
              onChange={setRetention}
              onSave={handleSaveRetention}
            />
          )}
          {section === 'hostname' && (
            <HostnamePane
              value={hostname}
              onChange={setHostname}
              onSave={handleSaveHostname}
            />
          )}
          {section === 'llm-profiles' && <LlmProfilesPane />}
        </div>
      </div>

      <div className="modal-action mt-4">
        <a href="/settings/" className="btn btn-ghost btn-sm">
          Operator dump
        </a>
        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
          Close
        </Button>
      </div>
    </Modal>
  )
}

export function BlueprintEditorPane({ blueprintId }: { blueprintId: string }) {
  const headingId = useId()
  const role = agentRole({ id: blueprintId, name: blueprintId })
  const [selectedFile, setSelectedFile] = useState<string | undefined>(undefined)

  useEffect(() => {
    setSelectedFile(undefined)
  }, [blueprintId])

  const sourceQuery = useQuery({
    queryKey: ['blueprint-source', blueprintId, selectedFile],
    queryFn: () => fetchBlueprintSource(blueprintId, selectedFile),
    enabled: Boolean(blueprintId),
    retry: false,
  })

  const live = sourceQuery.data
  const files = Array.isArray(live?.files) ? live.files : []
  const content = live?.content || (blueprintId ? fallbackBlueprintSource(blueprintId, role) : '')
  const fromLive = Boolean(live?.content)
  const modules = runtimeModulesFor(role)
  const highlighted = highlightPython(content)
  const label = blueprintId ? agentLabel({ id: blueprintId, name: titleCase(blueprintId) }) : 'Blueprint'

  return (
    <section id="os-blueprint-editor" aria-labelledby={headingId} className="space-y-3">
      <div>
        <h4 id={headingId} className="text-lg font-semibold">
          Blueprint
        </h4>
        <p className="mt-1 text-sm text-base-content/70">
          {blueprintId ? (
            <>
              Editing <span className="font-medium">{label}</span>
              {isExampleRole(role) ? (
                <>
                  {' '}
                  (<span className="font-mono">{role}</span> role).
                </>
              ) : (
                '.'
              )}{' '}
              This editor opens the Python/API recipe (tools, prompts, code) — not the Teams roster.
            </>
          ) : (
            'Select a roled agent in the rail to open its blueprint.'
          )}
        </p>
      </div>

      {modules.length > 0 && (
        <p className="text-xs text-base-content/60">
          Runtime modules (open when present on this checkout):{' '}
          {modules.map((mod, index) => (
            <span key={mod.path}>
              {index > 0 ? ', ' : null}
              <ModuleLink blueprintId={blueprintId} file={mod} source={live} />
            </span>
          ))}
        </p>
      )}

      {sourceQuery.isError && (
        <Alert type="info" icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">
            No live <code>/v1/blueprints/{blueprintId}/source</code> file. Showing the
            design recipe so you can see how the role behaves.
          </span>
        </Alert>
      )}

      {files.length > 1 && (
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Blueprint files">
          {files.map((file) => {
            const name = file.name
            const active = (live?.selected || live?.primary) === name
            return (
              <button
                key={name}
                type="button"
                role="tab"
                aria-selected={active}
                className={`btn btn-xs ${active ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => setSelectedFile(name)}
              >
                {name}
              </button>
            )
          })}
        </div>
      )}

      {blueprintId ? (
        <pre className={PYTHON_CODE_CLASS} tabIndex={0} aria-label={`${label} blueprint Python`}>
          <code
            className="language-python"
            dangerouslySetInnerHTML={{ __html: highlighted }}
          />
        </pre>
      ) : (
        <p className="text-sm text-base-content/60">No blueprint selected.</p>
      )}

      {fromLive && live?.selected && (
        <p className="text-xs text-base-content/50">
          <FileCode2 className="mr-1 inline h-3.5 w-3.5" aria-hidden="true" />
          {live.selected}
        </p>
      )}
    </section>
  )
}

function titleCase(id: string): string {
  if (!id) return id
  return id.charAt(0).toUpperCase() + id.slice(1)
}

function ModuleLink({
  blueprintId,
  file,
  source,
}: {
  blueprintId: string
  file: { label: string; path: string }
  source?: BlueprintSource
}) {
  const fileName = file.path.split('/').pop() || file.path
  const listed = source?.files?.some((entry) => entry.name === fileName)
  if (listed) {
    return (
      <a
        className="link font-mono"
        href={`/v1/blueprints/${encodeURIComponent(blueprintId)}/source?file=${encodeURIComponent(fileName)}`}
        target="_blank"
        rel="noreferrer"
      >
        {file.label}
      </a>
    )
  }
  return (
    <code title={file.path} className="font-mono">
      {file.label}
    </code>
  )
}

function RemotePane({
  section,
  herdr,
  onAddedHerdr,
}: {
  section: SettingsSection
  herdr?: RemoteConnection
  onAddedHerdr?: () => void
}) {
  if (section === 'remotes-add') {
    return <AddRemotePane onAddedHerdr={onAddedHerdr} />
  }
  if (section === 'remotes-herdr') {
    return <HerdrRemotePane remote={herdr} />
  }
  const remote = REMOTE_PANES.find((item) => item.id === section)
  const label = remote?.label ?? 'Remote'
  return (
    <div className="space-y-3">
      <h4 className="text-lg font-semibold">{label}</h4>
      <Alert type="info" icon={<Server className="h-5 w-5" />}>
        <div className="space-y-1 text-sm">
          <p>
            <span className="font-medium">{label}</span> is a placeholder remote.
            The remotes API has not landed — this pane is the settings-sheet
            shell only.
          </p>
          <p className="text-base-content/70">
            Hermes, OMB, and Rakazo will connect here once the backend exists.
          </p>
        </div>
      </Alert>
    </div>
  )
}

function AddRemotePane({ onAddedHerdr }: { onAddedHerdr?: () => void }) {
  const { success, error } = useToast()
  const queryClient = useQueryClient()
  const [kind, setKind] = useState('herdr')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKeyEnv, setApiKeyEnv] = useState('HERDR_API_KEY')
  const addRemote = useMutation({
    mutationFn: () =>
      persistRemote(kind, {
        base_url: baseUrl.trim(),
        api_key: apiKeyEnv.trim() ? `\${${apiKeyEnv.trim()}}` : undefined,
      }),
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: REMOTES_QUERY_KEY })
      success('Remote added', `${saved.id} · ${saved.base_url}`)
      if (saved.id === 'herdr') {
        onAddedHerdr?.()
      }
    },
    onError: (err: unknown) => {
      error('Could not add remote', err instanceof Error ? err.message : String(err))
    },
  })

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!baseUrl.trim()) {
      error('Base URL required', 'Add a base URL. Missing config is an error, not another host.')
      return
    }
    addRemote.mutate()
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div>
        <h4 className="text-lg font-semibold">Add remote</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Pick a kind, then a base URL and api-key-env name. Herdr appears in
          Settings Remotes only after you add it. CLI <code>--remote</code> uses
          that configured base. Localhost omits the flag only when you set a
          loopback URL.
        </p>
      </div>
      <Select
        label="Kind"
        name="remote-kind"
        value={kind}
        onChange={(event) => {
          const next = event.target.value
          setKind(next)
          if (next === 'herdr' && !apiKeyEnv.trim()) setApiKeyEnv('HERDR_API_KEY')
        }}
      >
        <option value="herdr">Herdr</option>
        <option value="hermes">Hermes</option>
        <option value="omb">OpenMousBot</option>
        <option value="rakazo">Rakazo</option>
      </Select>
      <Input
        label="Base URL"
        name="remote-base-url"
        value={baseUrl}
        onChange={(event) => setBaseUrl(event.target.value)}
        placeholder="http://127.0.0.1:9"
        autoComplete="off"
        spellCheck={false}
      />
      <Input
        label="API key env name"
        name="remote-api-key-env"
        value={apiKeyEnv}
        onChange={(event) => setApiKeyEnv(event.target.value)}
        placeholder="HERDR_API_KEY"
        autoComplete="off"
        spellCheck={false}
      />
      <Button type="submit" variant="primary" size="sm" loading={addRemote.isPending}>
        <Plus className="h-4 w-4" aria-hidden="true" />
        Add remote
      </Button>
    </form>
  )
}

function HerdrRemotePane({ remote }: { remote?: RemoteConnection }) {
  const { error } = useToast()
  const [health, setHealth] = useState<string>('')
  const [listed, setListed] = useState<string>('')
  const healthMut = useMutation({
    mutationFn: () => probeRemoteHealth('herdr'),
    onSuccess: (result) => {
      setHealth(`${result.state} — ${result.detail}`)
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : String(err)
      setHealth(message)
      error('Herdr health failed', message)
    },
  })
  const listMut = useMutation({
    mutationFn: () => operateRemote('herdr', { op: 'list' }),
    onSuccess: (result) => {
      setListed(result.detail)
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : String(err)
      setListed(message)
      error('Herdr list failed', message)
    },
  })

  if (!remote) {
    return (
      <div className="space-y-3">
        <h4 className="text-lg font-semibold">Herdr</h4>
        <Alert type="warning" icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">
            Herdr remote is not configured. Add kind=herdr with a base URL and
            api-key-env name. We will not guess another host.
          </span>
        </Alert>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-lg font-semibold">Herdr</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Configured base <code>{remote.base_url}</code>. CLI{' '}
          <code>--remote</code> uses this base. Auth env placeholder only
          {remote.api_key_set ? ' (resolved).' : ' (unset).'}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          loading={healthMut.isPending}
          onClick={() => healthMut.mutate()}
        >
          Health
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          loading={listMut.isPending}
          onClick={() => listMut.mutate()}
        >
          List
        </Button>
      </div>
      {health ? <p className="text-sm">Health: {health}</p> : null}
      {listed ? <p className="text-sm">List: {listed}</p> : null}
    </div>
  )
}

function RetentionPane({
  value,
  onChange,
  onSave,
}: {
  value: RetentionMode
  onChange: (mode: RetentionMode) => void
  onSave: (event: FormEvent) => void
}) {
  return (
    <form className="space-y-4" onSubmit={onSave}>
      <div>
        <h4 className="text-lg font-semibold">Retention</h4>
        <p className="mt-1 text-sm text-base-content/70">
          How this browser keeps chat leftovers. Saved locally until a storage
          API is wired.
        </p>
      </div>
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Mode</legend>
        <div className="join" role="radiogroup" aria-label="Retention mode">
          {RETENTION_MODES.map((mode) => (
            <input
              key={mode}
              className="join-item btn"
              type="radio"
              name="retention-mode"
              aria-label={RETENTION_MODE_LABELS[mode]}
              checked={value === mode}
              onChange={() => onChange(mode)}
            />
          ))}
        </div>
      </fieldset>
      <Button type="submit" variant="primary" size="sm">
        Save retention
      </Button>
    </form>
  )
}

function HostnamePane({
  value,
  onChange,
  onSave,
}: {
  value: string
  onChange: (next: string) => void
  onSave: (event: FormEvent) => void
}) {
  const detected = detectedHostname()
  return (
    <form className="space-y-4" onSubmit={onSave}>
      <div>
        <h4 className="text-lg font-semibold">Hostname</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Override the hostname this browser advertises. Leave blank to use the
          detected host{detected ? ` (${detected})` : ''}.
        </p>
      </div>
      <Input
        label="Hostname override"
        name="hostname-override"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={detected || 'swarm.example.com'}
        autoComplete="off"
        spellCheck={false}
      />
      <Button type="submit" variant="primary" size="sm">
        Save hostname
      </Button>
    </form>
  )
}

function LlmProfilesPane() {
  const profilesQuery = useQuery({
    queryKey: ['settings-llm-profiles'],
    queryFn: fetchModels,
    retry: 1,
  })
  const models = profilesQuery.data?.data ?? []

  return (
    <div className="space-y-3">
      <h4 className="text-lg font-semibold">LLM profiles</h4>
      <p className="text-sm text-base-content/70">
        Detected models from <code>/v1/models/</code>. Edit profiles on the
        Django operator dump.
      </p>
      {profilesQuery.isPending ? (
        <p className="text-sm text-base-content/60">Loading profiles…</p>
      ) : profilesQuery.isError ? (
        <Alert type="warning" icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">
            Could not load models. Open the{' '}
            <a href="/profiles/" className="link">
              LLM profiles
            </a>{' '}
            operator page.
          </span>
        </Alert>
      ) : models.length === 0 ? (
        <Alert type="info" icon={<Server className="h-5 w-5" />}>
          <span className="text-sm">
            No models reported. Review{' '}
            <a href="/profiles/" className="link">
              /profiles/
            </a>{' '}
            or the full{' '}
            <a href="/settings/" className="link">
              settings dump
            </a>
            .
          </span>
        </Alert>
      ) : (
        <ul className="space-y-1 text-sm">
          {models.map((model) => (
            <li
              key={model.id}
              className="rounded-lg border border-base-300 bg-base-200/60 px-3 py-2 font-mono"
            >
              {model.id}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
