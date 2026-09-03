import { useEffect, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, Server } from 'lucide-react'
import { Alert, Button, Input, Modal, useToast } from './DaisyUI'
import { fetchModels } from '../lib/api'
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

/** Window event so the command palette (and tests) can open the sheet. */
export const OPEN_SETTINGS_EVENT = 'swarm:open-settings'

export type SettingsSection =
  | 'remotes-hermes'
  | 'remotes-omb'
  | 'remotes-rakazo'
  | 'retention'
  | 'hostname'
  | 'llm-profiles'

const REMOTE_PANES = [
  { id: 'remotes-hermes' as const, label: 'Hermes' },
  { id: 'remotes-omb' as const, label: 'OMB' },
  { id: 'remotes-rakazo' as const, label: 'Rakazo' },
]

function isRemoteSection(section: SettingsSection): boolean {
  return section.startsWith('remotes-')
}

export interface SettingsSheetProps {
  isOpen: boolean
  onClose: () => void
}

/**
 * Right-docked DaisyUI settings sheet (REQ-19).
 *
 * Opens as `modal` + `modal-end` over the SPA (not a top-nav eject to Django).
 * Inner nav is DaisyUI `menu` + `menu-dropdown`. Retention uses `join` radios.
 * Remotes are placeholders until a remotes API lands. Django `/settings/` stays
 * the operator dump.
 */
export default function SettingsSheet({ isOpen, onClose }: SettingsSheetProps) {
  const { success } = useToast()
  const [section, setSection] = useState<SettingsSection>('retention')
  const [remotesOpen, setRemotesOpen] = useState(true)
  const [hostname, setHostname] = useState(() => loadHostnameOverride())
  const [retention, setRetention] = useState<RetentionMode>(() => loadRetentionMode())

  useEffect(() => {
    if (!isOpen) return
    setHostname(loadHostnameOverride())
    setRetention(loadRetentionMode())
  }, [isOpen])

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
      <div className="flex min-h-[24rem] flex-1 gap-0 overflow-hidden rounded-box border border-base-300">
        <nav aria-label="Settings sections" className="w-44 shrink-0 border-r border-base-300 bg-base-200 sm:w-52">
          <ul className="menu menu-md w-full rounded-none p-2">
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
          {isRemoteSection(section) && <RemotePane section={section} />}
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

function RemotePane({ section }: { section: SettingsSection }) {
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
