import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, FileCode2, HardDrive, Plus, Server } from 'lucide-react'
import { Alert, Button, Input, Modal, Select, useToast } from './DaisyUI'
import DefinitionPane from './DefinitionPane'
import AvatarThemePicker from './AvatarThemePicker'
import EnvOverrideBadge from './EnvOverrideBadge'
import McpServersPane from './McpServersPane'
import CliAgentsSettingsPane from './CliAgentsSettingsPane'
import ImageGenPane from './ImageGenSettings'
import {
  EMPTY_LOCAL_STORE,
  createRemote,
  deleteRemote,
  fetchBlueprintSource,
  fetchBlueprints,
  fetchConfigOwnership,
  fetchLlmProfiles,
  fetchLocalStore,
  fetchRemotes,
  patchConfigSection,
  patchLlmProfiles,
  type Blueprint,
  type BlueprintSource,
  type LlmTaskClass,
} from '../lib/api'
import { formatStoreSize } from '../lib/localStore'
import { RemoteSelect } from './RemoteSelect'
import { RemoteOperatePane } from './RemotesSettings'
import {
  configuredRemotes,
  remoteKindLabel,
  remoteKinds,
  unusedRemoteKinds,
} from '../lib/remotes'
import { TASK_CLASS_LABELS, missingProfileWarning, uiStatusWarnings } from '../lib/llmProfiles'
import {
  agentRole,
  exampleRoleAgents,
  fallbackBlueprintSource,
  isExampleRole,
  runtimeModulesFor,
} from '../lib/agentRoles'
import { roleDisplayName } from '../lib/safety'
import type { DefinitionKind } from '../lib/definitionExplain'
import { PYTHON_CODE_CLASS, highlightPython } from '../lib/highlightPython'
import {
  detectedHostname,
  loadBumpCompleted,
  loadHostnameOverride,
  saveBumpCompleted,
} from '../lib/settingsPrefs'
import { HOSTNAME_CHANGED_EVENT, dispatchHostnameChanged } from '../lib/hostname'
import { agentLabel, catalogLabel } from '../lib/supportAgent'
import { applyHostnameOverride, fetchUserPrefs, saveUserPrefs } from '../lib/userPrefs'
import {
  initialNavbarThemeVisible,
  initialTheme,
  dispatchSetNavbarThemeVisible,
  dispatchSetTheme,
  THEME_NAVBAR_SET_EVENT,
  THEME_SET_EVENT,
  type Theme,
} from '../lib/theme'

/** Window event so the rail hover-edit, command palette, and tests can open the sheet. */
export const OPEN_SETTINGS_EVENT = 'swarm:open-settings'

export type SettingsSection =
  | 'general'
  | 'definition'
  | 'blueprint'
  | 'remotes'
  | 'retention'
  | 'hostname'
  | 'llm-profiles'
  | 'mcp'
  | 'cli-agents'
  | 'rail'
  | 'image-gen'
  | 'system'

export interface OpenSettingsDetail {
  section?: SettingsSection
  blueprintId?: string
  teamId?: string
  definitionKind?: DefinitionKind
  definitionId?: string
  /** Open the Remotes pane already on the add form (zero-remotes bind path). */
  addRemote?: boolean
}

export function openSettingsSheet(detail?: OpenSettingsDetail): void {
  window.dispatchEvent(new CustomEvent<OpenSettingsDetail>(OPEN_SETTINGS_EVENT, { detail }))
}

export interface SettingsSheetProps {
  isOpen: boolean
  onClose: () => void
  blueprintId?: string | null
  teamId?: string | null
  initialSection?: SettingsSection | null
  definitionKind?: DefinitionKind | null
  definitionId?: string | null
  initialAddRemote?: boolean
}

/**
 * Right-docked DaisyUI settings sheet (REQ-19 + REQ-25).
 *
 * Opens as `modal` + `modal-end` over the SPA (not a top-nav eject to Django).
 * Gear opens Remotes / Retention / Hostname / LLM profiles / System. Blueprints
 * is a catalog list (same ids the agent-editor picker uses). Selecting an item
 * shows that recipe — not Remotes. Django `/settings/` stays the operator dump.
 */
export default function SettingsSheet({
  isOpen,
  onClose,
  blueprintId,
  teamId,
  initialSection,
  definitionKind,
  definitionId,
  initialAddRemote = false,
}: SettingsSheetProps) {
  const { success } = useToast()
  const [section, setSection] = useState<SettingsSection>('retention')
  const [hostname, setHostname] = useState(() => loadHostnameOverride())
  const [selectedBlueprintId, setSelectedBlueprintId] = useState(blueprintId || '')
  const [bumpCompleted, setBumpCompleted] = useState(() => loadBumpCompleted())
  const resolvedDefinitionId = definitionId || teamId || blueprintId || ''
  const resolvedKind: DefinitionKind =
    definitionKind || (teamId ? 'team' : blueprintId ? 'role' : 'blueprint')

  useEffect(() => {
    if (!isOpen) return
    void fetchUserPrefs().then((server) => {
      if (server && !server.empty) {
        applyHostnameOverride(server.hostname_override)
        setHostname(server.hostname_override)
        return
      }
      setHostname(loadHostnameOverride())
    })
    setBumpCompleted(loadBumpCompleted())
    if (initialSection) {
      setSection(initialSection)
    } else if (blueprintId) {
      setSection('blueprint')
      setSelectedBlueprintId(blueprintId)
    } else {
      setSection((current) =>
        current === 'blueprint' || current === 'definition' ? 'retention' : current,
      )
    }
  }, [isOpen, blueprintId, initialSection])

  useEffect(() => {
    const onHostnameChanged = (event: Event) => {
      const custom = event as CustomEvent<{ hostname?: string }>
      const updated = custom.detail?.hostname
      if (typeof updated === 'string') {
        setHostname(updated)
      } else {
        setHostname(loadHostnameOverride())
      }
    }
    window.addEventListener(HOSTNAME_CHANGED_EVENT, onHostnameChanged)
    return () => window.removeEventListener(HOSTNAME_CHANGED_EVENT, onHostnameChanged)
  }, [])

  const handleSaveHostname = (event: FormEvent) => {
    event.preventDefault()
    const next = applyHostnameOverride(hostname)
    setHostname(next)
    dispatchHostnameChanged(next)
    void saveUserPrefs({ hostname_override: next })
    success('Hostname saved', 'Override stored for this account.')
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
          <div className="flex items-center gap-2 px-3 pt-3 pb-1">
            <img
              src="/webui-geometric.svg"
              alt=""
              width={28}
              height={28}
              className="os-brand-mark-geometric shrink-0"
            />
            <span className="text-sm font-semibold tracking-tight">Open Swarm</span>
          </div>
          <ul className="menu menu-md w-full rounded-none p-2">
            <li>
              <button
                type="button"
                className={section === 'general' ? 'menu-active' : undefined}
                aria-current={section === 'general' ? 'page' : undefined}
                onClick={() => setSection('general')}
              >
                General
              </button>
            </li>
            <li>
              <button
                type="button"
                className={section === 'definition' ? 'menu-active' : undefined}
                aria-current={section === 'definition' ? 'page' : undefined}
                onClick={() => setSection('definition')}
              >
                Definition
              </button>
            </li>
            <li>
              <button
                type="button"
                className={section === 'blueprint' ? 'menu-active' : undefined}
                aria-current={section === 'blueprint' ? 'page' : undefined}
                onClick={() => setSection('blueprint')}
              >
                Blueprints
              </button>
            </li>
            <li>
              <button
                type="button"
                className={section === 'remotes' ? 'menu-active' : undefined}
                aria-current={section === 'remotes' ? 'page' : undefined}
                onClick={() => setSection('remotes')}
              >
                Remotes
              </button>
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
                Show LLM profiles
              </button>
            </li>
            <li>
              <button
                type="button"
                className={section === 'mcp' ? 'menu-active' : undefined}
                aria-current={section === 'mcp' ? 'page' : undefined}
                onClick={() => setSection('mcp')}
              >
                MCP servers
              </button>
            </li>
            <li>
              <button
                type="button"
                className={section === 'cli-agents' ? 'menu-active' : undefined}
                aria-current={section === 'cli-agents' ? 'page' : undefined}
                onClick={() => setSection('cli-agents')}
              >
                CLI agents
              </button>
            </li>
            <li>
              <button
                type="button"
                className={section === 'rail' ? 'menu-active' : undefined}
                aria-current={section === 'rail' ? 'page' : undefined}
                onClick={() => setSection('rail')}
              >
                Rail
              </button>
            </li>
            <li>
              <button
                type="button"
                className={section === 'image-gen' ? 'menu-active' : undefined}
                aria-current={section === 'image-gen' ? 'page' : undefined}
                onClick={() => setSection('image-gen')}
              >
                Image generation
              </button>
            </li>
            <li>
              <button
                type="button"
                className={section === 'system' ? 'menu-active' : undefined}
                aria-current={section === 'system' ? 'page' : undefined}
                onClick={() => setSection('system')}
              >
                System
              </button>
            </li>
          </ul>
        </nav>

        <div className="min-w-0 flex-1 overflow-y-auto bg-base-100 p-4 sm:p-5">
          {section === 'general' && <GeneralPane />}
          {section === 'definition' && (
            <DefinitionPane
              kind={resolvedKind}
              definitionId={resolvedDefinitionId}
              role={resolvedDefinitionId ? agentRole({ id: resolvedDefinitionId }) : undefined}
            />
          )}
          {section === 'blueprint' && (
            <BlueprintsListPane
              selectedId={selectedBlueprintId}
              onSelect={setSelectedBlueprintId}
            />
          )}
          {section === 'remotes' && <RemotesCatalogPane startAdding={initialAddRemote} />}
          {section === 'retention' && <RetentionPane />}
          {section === 'hostname' && (
            <HostnamePane
              value={hostname}
              onChange={setHostname}
              onSave={handleSaveHostname}
            />
          )}
          {section === 'llm-profiles' && <LlmProfilesPane />}
          {section === 'mcp' && <McpServersPane />}
          {section === 'cli-agents' && <CliAgentsSettingsPane />}
          {section === 'rail' && (
            <RailPane
              bumpCompleted={bumpCompleted}
              onBumpCompleted={(next) => {
                setBumpCompleted(next)
                saveBumpCompleted(next)
              }}
            />
          )}
          {section === 'image-gen' && <ImageGenPane />}
          {section === 'system' && <SystemPane />}
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

const EMPTY_BLUEPRINTS: Blueprint[] = []

export function BlueprintsListPane({
  selectedId,
  onSelect,
}: {
  selectedId: string
  onSelect: (id: string) => void
}) {
  const headingId = useId()
  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
    retry: 1,
  })
  const catalog = exampleRoleAgents(blueprintsQuery.data?.data ?? EMPTY_BLUEPRINTS)
  const ids = new Set(catalog.map((item) => item.id))
  const extras =
    selectedId && !ids.has(selectedId)
      ? [{ id: selectedId, name: selectedId } as Blueprint]
      : []
  const items = [...catalog, ...extras]

  return (
    <section aria-labelledby={headingId} className="space-y-4">
      <div>
        <h4 id={headingId} className="text-lg font-semibold">
          Blueprints
        </h4>
        <p className="mt-1 text-sm text-base-content/70">
          Catalog recipes this instance can assign to an agent. Select one to
          inspect its Python — this is not Remotes or other instance Settings.
        </p>
      </div>
      {blueprintsQuery.isPending ? (
        <p className="text-sm text-base-content/60">Loading blueprints…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-base-content/60">No blueprints in the catalog.</p>
      ) : (
        <ul role="listbox" aria-label="Blueprints" className="menu menu-md rounded-box border border-base-300 bg-base-200 p-2 os-scrollable-picker-list">
          {items.map((item) => {
            const selected = item.id === selectedId
            return (
              <li key={item.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  className={selected ? 'menu-active' : undefined}
                  onClick={() => onSelect(item.id)}
                >
                  {catalogLabel(item)}
                </button>
              </li>
            )
          })}
        </ul>
      )}
      {selectedId ? <BlueprintEditorPane blueprintId={selectedId} /> : null}
    </section>
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
  const label = blueprintId
    ? role === 'gate'
      ? roleDisplayName(role)
      : agentLabel({ id: blueprintId, name: titleCase(blueprintId) })
    : 'Blueprint'

  return (
    <section id="os-blueprint-editor" aria-labelledby={headingId} className="space-y-3">
      <div>
        <h4 id={headingId} className="text-lg font-semibold">
          Blueprint
        </h4>
        <p className="mt-1 text-sm text-base-content/70">
          {blueprintId ? (
            <>
              Viewing <span className="font-medium">{label}</span>
              {isExampleRole(role) ? (
                <>
                  {' '}
                  (<span className="font-mono">{role}</span> role).
                </>
              ) : (
                '.'
              )}{' '}
              This view displays the Python/API recipe (tools, prompts, code) — not the Teams roster.
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

function RemotesCatalogPane({ startAdding = false }: { startAdding?: boolean }) {
  const { success, error: toastError } = useToast()
  const queryClient = useQueryClient()
  const [adding, setAdding] = useState(startAdding)
  const [kind, setKind] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKeyEnv, setApiKeyEnv] = useState('')
  const [selectedId, setSelectedId] = useState('')

  const remotesQuery = useQuery({
    queryKey: ['settings-remotes'],
    queryFn: fetchRemotes,
    retry: 1,
  })
  const catalog = remotesQuery.data
  const configured = configuredRemotes(catalog)
  const kinds = remoteKinds(catalog)
  const unused = unusedRemoteKinds(catalog)

  useEffect(() => {
    if (!kind && unused[0]) setKind(unused[0].id)
  }, [kind, unused])

  useEffect(() => {
    if (!selectedId && configured[0]) setSelectedId(configured[0].id)
  }, [selectedId, configured])

  useEffect(() => {
    if (startAdding) setAdding(true)
  }, [startAdding])

  const addMutation = useMutation({
    mutationFn: () =>
      createRemote({
        kind,
        ...(baseUrl.trim() ? { base_url: baseUrl.trim() } : {}),
        ...(apiKeyEnv.trim() ? { api_key_env: apiKeyEnv.trim() } : {}),
      }),
    onSuccess: (created) => {
      queryClient.setQueryData(['settings-remotes'], (prev: Awaited<ReturnType<typeof fetchRemotes>> | undefined) => ({
        object: 'list' as const,
        kinds: remoteKinds(prev),
        configured: [...configuredRemotes(prev).filter((row) => row.id !== created.id), created],
        data: prev?.data ?? [],
      }))
      void queryClient.invalidateQueries({ queryKey: ['settings-remotes'] })
      void queryClient.invalidateQueries({ queryKey: ['configured-remotes'] })
      setAdding(false)
      setBaseUrl('')
      setApiKeyEnv('')
      setKind('')
      setSelectedId(created.id)
      success('Remote added', `${remoteKindLabel(created.kind || created.id, kinds)} is now configured.`)
    },
    onError: (err: Error) => {
      toastError('Could not add remote', err.message)
    },
  })

  const removeMutation = useMutation({
    mutationFn: (remoteId: string) => deleteRemote(remoteId),
    onSuccess: (_void, remoteId) => {
      queryClient.setQueryData(['settings-remotes'], (prev: Awaited<ReturnType<typeof fetchRemotes>> | undefined) => ({
        object: 'list' as const,
        kinds: remoteKinds(prev),
        configured: configuredRemotes(prev).filter((row) => row.id !== remoteId),
        data: prev?.data ?? [],
      }))
      void queryClient.invalidateQueries({ queryKey: ['settings-remotes'] })
      void queryClient.invalidateQueries({ queryKey: ['configured-remotes'] })
      if (selectedId === remoteId) setSelectedId('')
      success('Remote removed', 'Dropped from Settings and remote dropdowns.')
    },
    onError: (err: Error) => {
      toastError('Could not remove remote', err.message)
    },
  })

  const handleAdd = (event: FormEvent) => {
    event.preventDefault()
    if (!kind) return
    addMutation.mutate()
  }

  const selected = configured.find((remote) => remote.id === selectedId)

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-lg font-semibold">Remotes</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Only remotes you add appear here and in remote dropdowns. Unused kinds
          stay off the list.
        </p>
      </div>

      {remotesQuery.isPending ? (
        <p className="text-sm text-base-content/60" data-testid="remotes-loading">
          Loading remotes…
        </p>
      ) : remotesQuery.isError ? (
        <div className="space-y-3" data-testid="remotes-error">
          <Alert type="error" icon={<AlertCircle className="h-5 w-5" />}>
            <span className="text-sm">Failed to load remotes catalog.</span>
          </Alert>
          <button
            type="button"
            className="btn btn-sm btn-outline"
            onClick={() => void remotesQuery.refetch()}
          >
            Retry
          </button>
        </div>
      ) : (
        <>
          {configured.length > 0 ? (
            <RemoteSelect
              remotes={catalog}
              value={selectedId}
              onChange={setSelectedId}
              label="Remote"
            />
          ) : null}

          {configured.length === 0 && !adding ? (
            <Alert type="info" icon={<Server className="h-5 w-5" />}>
              <span className="text-sm">No remotes configured yet.</span>
            </Alert>
          ) : configured.length === 0 ? null : (
            <ul className="space-y-2 os-scrollable-picker-list" aria-label="Configured remotes">
              {configured.map((remote) => {
                const label = remoteKindLabel(remote.kind || remote.id, kinds)
                return (
                  <li
                    key={remote.id}
                    className="flex items-start justify-between gap-3 rounded-lg border border-base-300 bg-base-200/60 px-3 py-2"
                  >
                    <div className="min-w-0">
                      <p className="font-medium">{label}</p>
                      <p className="truncate font-mono text-xs text-base-content/60">
                        {remote.base_url || 'localhost'}
                      </p>
                      <div className="mt-1">
                        <EnvOverrideBadge badge={remote.provenance?.base_url} />
                      </div>
                      {remote.provenance?.api_key ? (
                        <div className="mt-1">
                          <EnvOverrideBadge badge={remote.provenance.api_key} />
                        </div>
                      ) : null}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="xs"
                      onClick={() => removeMutation.mutate(remote.id)}
                      disabled={removeMutation.isPending}
                    >
                      Remove
                    </Button>
                  </li>
                )
              })}
            </ul>
          )}

          {selected ? <RemoteOperatePane remote={selected} /> : null}

          {adding ? (
            <form className="space-y-3 rounded-box border border-base-300 p-3" onSubmit={handleAdd}>
              <Select
                label="Kind"
                name="remote-kind"
                size="sm"
                value={kind}
                onChange={(event) => setKind(event.target.value)}
              >
                {unused.length === 0 ? (
                  <option value="" disabled>
                    All kinds added
                  </option>
                ) : (
                  unused.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label}
                    </option>
                  ))
                )}
              </Select>
              <Input
                label="URL"
                name="remote-url"
                value={baseUrl}
                onChange={(event) => setBaseUrl(event.target.value)}
                placeholder={kind === 'swarm' ? 'http://127.0.0.1:9' : 'http://127.0.0.1:8802'}
                autoComplete="off"
                spellCheck={false}
              />
              {kind === 'swarm' ? (
                <p className="text-sm text-base-content/70">
                  Nested open-swarm is another process (own DB). Do not add this
                  instance as its own remote.
                </p>
              ) : null}
              <Input
                label="API key env (optional)"
                name="remote-api-key-env"
                value={apiKeyEnv}
                onChange={(event) => setApiKeyEnv(event.target.value)}
                placeholder="OMB_API_KEY"
                autoComplete="off"
                spellCheck={false}
              />
              <div className="flex flex-wrap gap-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={!kind || addMutation.isPending}
                >
                  Save remote
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setAdding(false)
                  }}
                >
                  Cancel
                </Button>
              </div>
            </form>
          ) : (
            <Button type="button" variant="outline" size="sm" onClick={() => setAdding(true)}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add remote
            </Button>
          )}
        </>
      )}
    </div>
  )
}

function RetentionPane() {
  return (
    <div className="space-y-4" data-testid="settings-retention-pane">
      <div>
        <h4 className="text-lg font-semibold">Retention</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Chat retention, archiving, and trash pruning are managed by the server storage engine.
        </p>
      </div>
      <div className="rounded-box border border-base-300 bg-base-200/50 p-4 space-y-3">
        <p className="text-sm text-base-content/80">
          To inspect chat disk usage, archive old sessions, or empty trash, open the server retention dashboard.
        </p>
        <div>
          <a
            href="/settings/#chat-retention-title"
            className="btn btn-sm btn-outline gap-2"
          >
            Server retention dashboard
          </a>
        </div>
      </div>
    </div>
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

function GeneralPane() {
  const [themePref, setThemePref] = useState<Theme>(initialTheme)
  const [navbarVisible, setNavbarVisible] = useState<boolean>(initialNavbarThemeVisible)

  useEffect(() => {
    const onSet = (event: Event) => {
      const detail = (event as CustomEvent<Theme>).detail
      if (detail === 'light' || detail === 'dark' || detail === 'system') {
        setThemePref(detail)
      }
    }
    const onNavbarToggle = (event: Event) => {
      const detail = (event as CustomEvent<boolean>).detail
      setNavbarVisible(Boolean(detail))
    }
    window.addEventListener(THEME_SET_EVENT, onSet)
    window.addEventListener(THEME_NAVBAR_SET_EVENT, onNavbarToggle)
    return () => {
      window.removeEventListener(THEME_SET_EVENT, onSet)
      window.removeEventListener(THEME_NAVBAR_SET_EVENT, onNavbarToggle)
    }
  }, [])

  const handleThemeChange = (value: Theme) => {
    setThemePref(value)
    dispatchSetTheme(value)
  }

  const handleNavbarChange = (visible: boolean) => {
    setNavbarVisible(visible)
    dispatchSetNavbarThemeVisible(visible)
  }

  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-lg font-semibold">General</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Preferences for display and browser behavior.
        </p>
      </div>

      <section aria-labelledby="os-visuals-heading" className="space-y-4">
        <h5
          id="os-visuals-heading"
          className="text-base font-semibold border-b border-base-200 pb-1"
        >
          Visuals
        </h5>

        <div className="form-control w-full max-w-xs space-y-1">
          <label htmlFor="os-theme-select" className="label py-0">
            <span className="label-text font-medium">Theme</span>
          </label>
          <select
            id="os-theme-select"
            aria-label="Theme"
            className="select select-bordered w-full"
            value={themePref}
            onChange={(e) => handleThemeChange(e.target.value as Theme)}
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">Use system</option>
          </select>
          <p className="text-xs text-base-content/60">
            Choose light, dark, or follow your operating system appearance (prefers-color-scheme).
          </p>
        </div>

        <div className="form-control">
          <label className="label cursor-pointer justify-start gap-4">
            <input
              type="checkbox"
              className="toggle"
              checked={navbarVisible}
              onChange={(e) => handleNavbarChange(e.target.checked)}
              aria-label="Show theme control in top bar"
            />
            <span className="label-text">Show theme control in top bar</span>
          </label>
          <p className="text-xs text-base-content/60">
            Show a quick theme toggle button in the top navigation bar.
          </p>
        </div>
      </section>
    </div>
  )
}

function RailPane({
  bumpCompleted,
  onBumpCompleted,
}: {
  bumpCompleted: boolean
  onBumpCompleted: (next: boolean) => void
}) {
  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-lg font-semibold">Rail</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Drag conversation rows to reorder them. Hidden stays its own list.
          Favourite tiles keep their own order.
        </p>
      </div>
      <label className="label cursor-pointer justify-start gap-4">
        <input
          type="checkbox"
          className="toggle"
          checked={bumpCompleted}
          onChange={(event) => onBumpCompleted(event.target.checked)}
          aria-label="Bump completed agents to top"
        />
        <span className="label-text">Bump completed agents to top</span>
      </label>
      <p className="text-sm text-base-content/60">
        On: when a generation finishes, that agent moves to the top of the
        visible list. Off: order changes only by drag.
      </p>
      <div className="pt-2 border-t border-base-200">
        <AvatarThemePicker />
      </div>
    </div>
  )
}

function SystemPane() {
  const headingId = useId()
  const storeQuery = useQuery({
    queryKey: ['settings-local-store'],
    queryFn: fetchLocalStore,
    retry: false,
    staleTime: 0,
    refetchOnMount: 'always',
  })
  const ownershipQuery = useQuery({
    queryKey: ['settings-config-ownership'],
    queryFn: fetchConfigOwnership,
    retry: false,
  })
  const facts = storeQuery.data || EMPTY_LOCAL_STORE
  const sizeLabel =
    facts.created && facts.size_bytes > 0
      ? facts.size_label || formatStoreSize(facts.size_bytes)
      : formatStoreSize(facts.size_bytes)
  const location = facts.path?.trim() || 'not created yet'

  return (
    <section id="os-system-store" aria-labelledby={headingId} className="space-y-4">
      <div>
        <h4 id={headingId} className="text-lg font-semibold">
          System
        </h4>
        <p className="mt-1 text-sm text-base-content/70">
          Local database on this machine. Read-only facts refresh when you open
          this section.
        </p>
      </div>
      {storeQuery.isPending ? (
        <p className="text-sm text-base-content/60">Loading local database…</p>
      ) : storeQuery.isError ? (
        <div className="space-y-3" data-testid="system-store-error">
          <Alert type="error" icon={<AlertCircle className="h-5 w-5" />}>
            <span className="text-sm">
              Failed to load local database facts. Check local daemon connection.
            </span>
          </Alert>
          <button
            type="button"
            className="btn btn-sm btn-outline"
            onClick={() => void storeQuery.refetch()}
          >
            Retry
          </button>
        </div>
      ) : (
        <dl className="space-y-3 text-sm">
          <div className="rounded-lg border border-base-300 bg-base-200/60 px-3 py-2">
            <dt className="text-xs uppercase tracking-wide text-base-content/60">Size</dt>
            <dd className="mt-0.5 font-medium">{sizeLabel}</dd>
          </div>
          <div className="rounded-lg border border-base-300 bg-base-200/60 px-3 py-2">
            <dt className="text-xs uppercase tracking-wide text-base-content/60">Location</dt>
            <dd className="mt-0.5 break-all font-mono text-xs">{location}</dd>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-base-300 bg-base-200/60 px-3 py-2">
              <dt className="text-xs uppercase tracking-wide text-base-content/60">Conversations</dt>
              <dd className="mt-0.5 font-medium">{facts.conversation_count}</dd>
            </div>
            <div className="rounded-lg border border-base-300 bg-base-200/60 px-3 py-2">
              <dt className="text-xs uppercase tracking-wide text-base-content/60">Messages</dt>
              <dd className="mt-0.5 font-medium">{facts.message_count}</dd>
            </div>
          </div>
        </dl>
      )}
      <p className="text-xs text-base-content/50">
        <HardDrive className="mr-1 inline h-3.5 w-3.5" aria-hidden="true" />
        Stored on this machine. No remote host.
      </p>

      {ownershipQuery.data?.object === 'config_ownership' ? (
        <div className="space-y-3 border-t border-base-200 pt-4" data-testid="config-coverage">
          <h5 className="text-sm font-semibold">Config coverage</h5>
          <p className="text-xs text-base-content/70">
            Decision: <strong>{ownershipQuery.data.decision}</strong> — {ownershipQuery.data.note}
          </p>
          {ownershipQuery.data.force_env ? (
            <EnvOverrideBadge
              badge={{
                kind: 'forced',
                label: `Forced by env ${ownershipQuery.data.force_env_var} (read-only)`,
                env_var: ownershipQuery.data.force_env_var,
                forced: true,
                editable: false,
              }}
            />
          ) : null}
          <p className="text-xs font-medium text-base-content/70">Advanced / not a dedicated pane</p>
          <ul className="list-disc space-y-1 pl-5 text-xs text-base-content/70">
            {(ownershipQuery.data.advanced_sections || []).map((key) => (
              <li key={key}>
                <code>{key}</code> — write via <code>/v1/config/sections/{key}/</code> or swarm-cli
              </li>
            ))}
          </ul>
          <p className="text-xs font-medium text-base-content/70">Secrets · env-only</p>
          <ul className="list-disc space-y-1 pl-5 text-xs text-base-content/70">
            {(ownershipQuery.data.inventory || [])
              .filter((row) => row.partition === 'env_only')
              .map((row) => (
                <li key={row.key}>
                  <code>{row.key}</code> — {row.notes}
                </li>
              ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

function LlmProfilesPane() {
  const { success, error: toastError } = useToast()
  const profilesQuery = useQuery({
    queryKey: ['settings-llm-profiles'],
    queryFn: fetchLlmProfiles,
    retry: 1,
  })
  const remote = profilesQuery.data
  const [defaultId, setDefaultId] = useState('')
  const [overrideOn, setOverrideOn] = useState(false)
  const [taskMap, setTaskMap] = useState<Partial<Record<LlmTaskClass, string>>>({})
  const [saving, setSaving] = useState(false)
  const [profileName, setProfileName] = useState('')
  const [profileModel, setProfileModel] = useState('')
  const [profileBaseUrl, setProfileBaseUrl] = useState('')
  const [profileKeyEnv, setProfileKeyEnv] = useState('OPENAI_API_KEY')
  const [addingProfile, setAddingProfile] = useState(false)
  const hydrated = useRef(false)
  const defaultBadge = remote?.provenance?.default_llm_profile
  const defaultForced = Boolean(defaultBadge?.forced)

  useEffect(() => {
    if (!remote || hydrated.current) return
    hydrated.current = true
    setDefaultId(remote.default_llm_profile || '')
    setOverrideOn(Boolean(remote.override_per_task))
    setTaskMap({ ...remote.task_llm_profiles })
  }, [remote])

  const profiles = remote?.profiles ?? []
  const ids = profiles.map((profile) => profile.id)
  const fallback = defaultId || remote?.default_llm_profile || 'default'
  const warnings = uiStatusWarnings(
    [
      ...(remote?.warnings ?? []),
      missingProfileWarning(defaultId, remote, fallback),
      ...((['orchestration', 'auxiliary', 'delegation'] as const).map((cls) =>
        overrideOn ? missingProfileWarning(taskMap[cls], remote, fallback) : null,
      )),
    ].filter((text): text is string => Boolean(text)),
  )

  const optionIds = Array.from(
    new Set(
      [
        ...ids,
        defaultId,
        ...Object.values(taskMap),
      ].filter((id): id is string => Boolean(id)),
    ),
  )

  const handleSave = async (event: FormEvent) => {
    event.preventDefault()
    if (profilesQuery.isError || profiles.length === 0) {
      return
    }
    setSaving(true)
    try {
      const payload: {
        default_llm_profile?: string
        override_per_task: boolean
        task_llm_profiles: Partial<Record<LlmTaskClass, string>>
      } = {
        override_per_task: overrideOn,
        task_llm_profiles: overrideOn
          ? {
              orchestration: taskMap.orchestration || defaultId,
              auxiliary: taskMap.auxiliary || defaultId,
              delegation: taskMap.delegation || defaultId,
            }
          : taskMap,
      }
      if (defaultId.trim()) {
        payload.default_llm_profile = defaultId.trim()
      }
      const saved = await patchLlmProfiles(payload)
      setDefaultId(saved.default_llm_profile || defaultId)
      setOverrideOn(Boolean(saved.override_per_task))
      setTaskMap({ ...saved.task_llm_profiles })
      success('LLM profiles saved', 'Default stored in settings.default_llm_profile.')
    } catch (err) {
      toastError(
        'Could not save LLM profiles',
        err instanceof Error ? err.message : 'Request failed.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="space-y-4" onSubmit={handleSave}>
      <div>
        <h4 className="text-lg font-semibold">LLM profiles</h4>
        <p className="text-sm text-base-content/70">
          Pick a Default from any connected CLI, API, or remote. Task-class
          names (orchestration / auxiliary / delegation) are roles, not required
          model ids. Auto-picks fill the map until you change them.
        </p>
      </div>

      {profilesQuery.isPending ? (
        <p className="text-sm text-base-content/60">Loading profiles…</p>
      ) : profilesQuery.isError ? (
        <Alert type="warning" icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">
            Could not load configured profiles. Chat still uses the server
            default when one is stored.
          </span>
        </Alert>
      ) : profiles.length === 0 ? (
        <Alert type="info" icon={<Server className="h-5 w-5" />}>
          <span className="text-sm">
            No connected models yet. Add a CLI, API, or remote — swarm will
            auto-assign a default from whatever you connect.
          </span>
        </Alert>
      ) : (
        <ul className="space-y-1 text-sm os-scrollable-picker-list" aria-label="Configured LLM profiles">
          {profiles.map((profile) => (
            <li
              key={`${profile.source}:${profile.id}`}
              className="rounded-lg border border-base-300 bg-base-200/60 px-3 py-2"
            >
              <span className="font-mono">{profile.id}</span>
              <span className="ml-2 text-xs text-base-content/60">
                {profile.source}
                {profile.owned_by ? ` · ${profile.owned_by}` : ''}
              </span>
            </li>
          ))}
        </ul>
      )}

      <Select
        label="Default"
        name="default-llm-profile"
        value={defaultId}
        onChange={(event) => setDefaultId(event.target.value)}
        size="sm"
        disabled={optionIds.length === 0 || defaultForced}
      >
        {optionIds.length === 0 ? (
          <option value="">No models connected</option>
        ) : null}
        {optionIds.map((id) => (
          <option key={id} value={id}>
            {id}
            {remote?.auto_picks?.default === id && remote.default_is_auto ? ' (auto)' : ''}
          </option>
        ))}
      </Select>
      {remote?.default_is_auto && remote.auto_picks?.default ? (
        <p className="text-xs text-base-content/60">
          Auto-picked Default: <code>{remote.auto_picks.default}</code>. Chat
          uses this until you save another id.
        </p>
      ) : null}
      <EnvOverrideBadge badge={defaultBadge} />

      {addingProfile ? (
        <div className="space-y-3 rounded-box border border-base-300 p-3">
          <p className="text-sm font-medium">Add LLM profile</p>
          <Input
            label="Profile id"
            name="llm-profile-id"
            value={profileName}
            onChange={(event) => setProfileName(event.target.value)}
            placeholder="local"
            autoComplete="off"
            spellCheck={false}
          />
          <Input
            label="Model"
            name="llm-profile-model"
            value={profileModel}
            onChange={(event) => setProfileModel(event.target.value)}
            placeholder="gpt-4o-mini"
            autoComplete="off"
            spellCheck={false}
          />
          <Input
            label="Base URL"
            name="llm-profile-base"
            value={profileBaseUrl}
            onChange={(event) => setProfileBaseUrl(event.target.value)}
            placeholder="https://api.openai.com/v1"
            autoComplete="off"
            spellCheck={false}
          />
          <Input
            label="API key env"
            name="llm-profile-key-env"
            value={profileKeyEnv}
            onChange={(event) => setProfileKeyEnv(event.target.value)}
            placeholder="OPENAI_API_KEY"
            autoComplete="off"
            spellCheck={false}
          />
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!profileName.trim() || !profileModel.trim()}
              onClick={async () => {
                try {
                  const envName = profileKeyEnv.trim() || 'OPENAI_API_KEY'
                  await patchConfigSection('llm', {
                    upsert: {
                      [profileName.trim()]: {
                        provider: 'openai',
                        model: profileModel.trim(),
                        ...(profileBaseUrl.trim() ? { base_url: profileBaseUrl.trim() } : {}),
                        api_key: `\${${envName}}`,
                      },
                    },
                  })
                  setAddingProfile(false)
                  setProfileName('')
                  setProfileModel('')
                  setProfileBaseUrl('')
                  success('LLM profile saved', 'Named profile stored in swarm_config.json llm.')
                  hydrated.current = false
                  await profilesQuery.refetch()
                } catch (err) {
                  toastError(
                    'Could not save LLM profile',
                    err instanceof Error ? err.message : 'Request failed.',
                  )
                }
              }}
            >
              Save profile
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setAddingProfile(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <Button type="button" variant="outline" size="sm" onClick={() => setAddingProfile(true)}>
          Add LLM profile
        </Button>
      )}

      <button
        type="button"
        role="switch"
        aria-checked={overrideOn}
        className="flex items-center gap-3 text-left"
        onClick={() => setOverrideOn((on) => !on)}
      >
        <input
          type="checkbox"
          className="toggle toggle-primary pointer-events-none"
          checked={overrideOn}
          readOnly
          tabIndex={-1}
          aria-hidden="true"
        />
        <span className="label-text">Override per task</span>
      </button>
      <p className="text-xs text-base-content/60">
        Off: every job uses Default. On: cheap summary stays on auxiliary,
        design / coding can use delegation.
      </p>

      {overrideOn ? (
        <fieldset className="space-y-3">
          <legend className="text-sm font-medium">Task class map</legend>
          {(['orchestration', 'auxiliary', 'delegation'] as const).map((cls) => (
            <Select
              key={cls}
              label={TASK_CLASS_LABELS[cls]}
              name={`task-llm-${cls}`}
              value={taskMap[cls] || defaultId}
              onChange={(event) =>
                setTaskMap((current) => ({ ...current, [cls]: event.target.value }))
              }
              size="sm"
              disabled={optionIds.length === 0}
            >
              {optionIds.map((id) => (
                <option key={`${cls}-${id}`} value={id}>
                  {id}
                </option>
              ))}
            </Select>
          ))}
        </fieldset>
      ) : null}

      {warnings.length > 0 ? (
        <Alert type="warning" icon={<AlertCircle className="h-5 w-5" />}>
          <ul className="space-y-1 text-sm">
            {warnings.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
        </Alert>
      ) : null}

      <Button
        type="submit"
        variant="primary"
        size="sm"
        disabled={
          saving ||
          profilesQuery.isPending ||
          profilesQuery.isError ||
          profiles.length === 0 ||
          defaultForced
        }
      >
        {saving ? 'Saving…' : 'Save LLM profiles'}
      </Button>
    </form>
  )
}
