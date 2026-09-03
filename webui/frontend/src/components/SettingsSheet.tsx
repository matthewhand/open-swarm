import { useEffect, useId, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, FileCode2, Server } from 'lucide-react'
import { Alert, Button, Input, Modal, useToast } from './DaisyUI'
import { fetchBlueprintSource, fetchModels, type BlueprintSource } from '../lib/api'
import RemotesSettings from './RemotesSettings'
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
  | 'remotes'
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

function isRemoteSection(section: SettingsSection | string): boolean {
  return section === 'remotes' || String(section).startsWith('remotes-')
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
  const [hostname, setHostname] = useState(() => loadHostnameOverride())
  const [retention, setRetention] = useState<RetentionMode>(() => loadRetentionMode())

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
                className={isRemoteSection(section) ? 'menu-active' : undefined}
                aria-current={isRemoteSection(section) ? 'page' : undefined}
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
          {section === 'blueprint' && (
            <BlueprintEditorPane blueprintId={blueprintId || ''} />
          )}
          {isRemoteSection(section) && <RemotesSettings />}
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
