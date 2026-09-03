import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, FileCode2, Plus, Server } from 'lucide-react'
import { Alert, Button, Input, Modal, Select, useToast } from './DaisyUI'
import DefinitionPane from './DefinitionPane'
import {
  createRemote,
  deleteRemote,
  fetchBlueprintSource,
  fetchLlmProfiles,
  fetchModels,
  fetchRemotes,
  patchLlmProfiles,
  type BlueprintSource,
  type LlmTaskClass,
} from '../lib/api'
import { RemoteSelect } from './RemoteSelect'
import {
  configuredRemotes,
  remoteKindLabel,
  remoteKinds,
  unusedRemoteKinds,
} from '../lib/remotes'
import { TASK_CLASS_LABELS, missingProfileWarning } from '../lib/llmProfiles'
import {
  agentRole,
  fallbackBlueprintSource,
  isExampleRole,
  runtimeModulesFor,
} from '../lib/agentRoles'
import type { DefinitionKind } from '../lib/definitionExplain'
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
  | 'definition'
  | 'blueprint'
  | 'remotes'
  | 'retention'
  | 'hostname'
  | 'llm-profiles'

export interface OpenSettingsDetail {
  section?: SettingsSection
  blueprintId?: string
  teamId?: string
  definitionKind?: DefinitionKind
  definitionId?: string
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
}

/**
 * Right-docked DaisyUI settings sheet (REQ-19 + REQ-25).
 *
 * Opens as `modal` + `modal-end` over the SPA (not a top-nav eject to Django).
 * Gear opens Remotes / Retention / Hostname / LLM profiles. Hover-edit on a
 * roled agent selects the Blueprint editor for that agent's blueprint id —
 * not the Teams drop-zone roster. Django `/settings/` stays the operator dump.
 */
export default function SettingsSheet({
  isOpen,
  onClose,
  blueprintId,
  teamId,
  initialSection,
  definitionKind,
  definitionId,
}: SettingsSheetProps) {
  const { success } = useToast()
  const [section, setSection] = useState<SettingsSection>('retention')
  const [hostname, setHostname] = useState(() => loadHostnameOverride())
  const [retention, setRetention] = useState<RetentionMode>(() => loadRetentionMode())
  const resolvedDefinitionId = definitionId || teamId || blueprintId || ''
  const resolvedKind: DefinitionKind =
    definitionKind || (teamId ? 'team' : blueprintId ? 'role' : 'blueprint')

  useEffect(() => {
    if (!isOpen) return
    setHostname(loadHostnameOverride())
    setRetention(loadRetentionMode())
    if (initialSection) {
      setSection(initialSection)
    } else if (blueprintId) {
      setSection('blueprint')
    } else if (initialSection) {
      setSection(initialSection)
    } else {
      setSection((current) =>
        current === 'blueprint' || current === 'definition' ? 'retention' : current,
      )
    }
  }, [isOpen, blueprintId, initialSection])

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
                Blueprint
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
                LLM profiles
              </button>
            </li>
          </ul>
        </nav>

        <div className="min-w-0 flex-1 overflow-y-auto bg-base-100 p-4 sm:p-5">
          {section === 'definition' && (
            <DefinitionPane
              kind={resolvedKind}
              definitionId={resolvedDefinitionId}
              role={resolvedDefinitionId ? agentRole({ id: resolvedDefinitionId }) : undefined}
            />
          )}
          {section === 'blueprint' && (
            <BlueprintEditorPane blueprintId={blueprintId || ''} />
          )}
          {section === 'remotes' && <RemotesCatalogPane />}
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

function RemotesCatalogPane() {
  const { success, error: toastError } = useToast()
  const queryClient = useQueryClient()
  const [adding, setAdding] = useState(false)
  const [kind, setKind] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
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

  const addMutation = useMutation({
    mutationFn: () =>
      createRemote({
        kind,
        ...(baseUrl.trim() ? { base_url: baseUrl.trim() } : {}),
        ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
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
      setApiKey('')
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

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-lg font-semibold">Remotes</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Only remotes you add appear here and in remote dropdowns. Unused kinds
          stay off the list.
        </p>
      </div>

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
        <ul className="space-y-2" aria-label="Configured remotes">
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
            label="API key"
            name="remote-api-key"
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="${API_KEY}"
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
                setApiKey('')
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
  const hydrated = useRef(false)

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
  const warnings = [
    ...(remote?.warnings ?? []),
    missingProfileWarning(defaultId, remote, fallback),
    ...((['orchestration', 'auxiliary', 'delegation'] as const).map((cls) =>
      overrideOn ? missingProfileWarning(taskMap[cls], remote, fallback) : null,
    )),
  ].filter((text, index, all): text is string => Boolean(text) && all.indexOf(text) === index)

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
    setSaving(true)
    try {
      const saved = await patchLlmProfiles({
        default_llm_profile: defaultId,
        override_per_task: overrideOn,
        task_llm_profiles: overrideOn
          ? {
              orchestration: taskMap.orchestration || defaultId,
              auxiliary: taskMap.auxiliary || defaultId,
              delegation: taskMap.delegation || defaultId,
            }
          : taskMap,
      })
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
        <ul className="space-y-1 text-sm" aria-label="Configured LLM profiles">
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
        disabled={optionIds.length === 0}
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

      <Button type="submit" variant="primary" size="sm" disabled={saving}>
        {saving ? 'Saving…' : 'Save LLM profiles'}
      </Button>
    </form>
  )
}
