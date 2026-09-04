import { useEffect, useId, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Input, Modal, Select } from './DaisyUI'
import {
  fetchBlueprints,
  fetchCliAgents,
  fetchCliModels,
  fetchLlmProfiles,
  fetchModels,
  type AgentRole,
  type Blueprint,
} from '../lib/api'
import {
  assignedBlueprintId,
  loadAgentEdit,
  saveAgentEdit,
} from '../lib/agentEdits'
import {
  NEW_CHAT_PER_TASK_LABEL,
  NEW_CHAT_PER_TASK_TOOLTIP,
  fetchAgentSettings,
  saveAgentSettings,
} from '../lib/agentSettings'
import { agentRole, exampleRoleAgents } from '../lib/agentRoles'
import { ROLE_BRIEFS } from '../lib/definitionExplain'
import { agentLabel, catalogLabel, sessionKindForAgent } from '../lib/supportAgent'
import { isCliBlueprintId } from '../lib/cliAgentContext'
import { openSettingsSheet } from './SettingsSheet'

/** Window event so the rail hover-edit and tests can open the agent editor. */
export const OPEN_AGENT_EDITOR_EVENT = 'swarm:open-agent-editor'

export interface OpenAgentEditorDetail {
  agentId: string
}

export function openAgentEditor(detail: OpenAgentEditorDetail): void {
  window.dispatchEvent(
    new CustomEvent<OpenAgentEditorDetail>(OPEN_AGENT_EDITOR_EVENT, { detail }),
  )
}

const ROLE_OPTIONS: { value: AgentRole; label: string }[] = [
  { value: 'default', label: 'default' },
  { value: 'support', label: 'support' },
  { value: 'gate', label: 'gate' },
  { value: 'skeptic', label: 'skeptic' },
]

const EMPTY_BLUEPRINTS: Blueprint[] = []

export interface AgentEditorProps {
  isOpen: boolean
  onClose: () => void
  agentId: string | null
}

/**
 * Agent-scoped editor overlay (REQ-58 / REQ-124).
 *
 * Name, role with explanation, which catalog blueprint this seat uses,
 * kind-appropriate LLM override (disabled for remotes, CLI->model for CLIs,
 * profile->model for API).
 */
export default function AgentEditor({ isOpen, onClose, agentId }: AgentEditorProps) {
  const id = agentId || ''
  const toggleId = useId()
  const [name, setName] = useState('')
  const [role, setRole] = useState<AgentRole>('default')
  const [blueprintId, setBlueprintId] = useState('')
  const [llmOverride, setLlmOverride] = useState('')
  const [cliOverride, setCliOverride] = useState('')
  const [profileOverride, setProfileOverride] = useState('')
  const [newChatPerTask, setNewChatPerTask] = useState(false)
  const [savingSettings, setSavingSettings] = useState(false)

  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
    enabled: isOpen,
    retry: 1,
  })

  const catalog = useMemo(
    () => exampleRoleAgents(blueprintsQuery.data?.data ?? EMPTY_BLUEPRINTS),
    [blueprintsQuery.data],
  )
  const agent = catalog.find((item) => item.id === id)
  const catalogName = agent ? agentLabel({ id: agent.id, name: agent.name }) : id
  const title = id ? `Edit ${catalogName}` : 'Edit agent'

  const agentKind = useMemo(() => {
    if (!id) return 'api'
    const lowerId = id.toLowerCase()
    if (lowerId.startsWith('remote-') || agent?.tags?.includes('remote') || lowerId.includes('remote')) {
      return 'remote'
    }
    if (
      lowerId.startsWith('cli-') ||
      isCliBlueprintId(id) ||
      agent?.tags?.includes('cli') ||
      lowerId.includes('cli')
    ) {
      return 'cli'
    }
    return sessionKindForAgent({ id, tags: agent?.tags })
  }, [id, agent])

  const cliQuery = useQuery({
    queryKey: ['cli-agents'],
    queryFn: fetchCliAgents,
    enabled: Boolean(isOpen && agentKind === 'cli'),
    retry: 1,
  })

  const activeCli = cliOverride || cliQuery.data?.clis?.[0] || ''

  const cliModelsQuery = useQuery({
    queryKey: ['cli-models', activeCli],
    queryFn: () => (activeCli ? fetchCliModels(activeCli) : Promise.resolve({ cli: '', models: [] })),
    enabled: Boolean(isOpen && agentKind === 'cli' && activeCli),
    retry: 1,
  })

  const llmProfilesQuery = useQuery({
    queryKey: ['llm-profiles'],
    queryFn: fetchLlmProfiles,
    enabled: Boolean(isOpen && agentKind === 'api'),
    retry: 1,
  })

  const modelsQuery = useQuery({
    queryKey: ['settings-llm-profiles'],
    queryFn: fetchModels,
    enabled: Boolean(isOpen && agentKind === 'api'),
    retry: 1,
  })

  const catalogAgentIds = useMemo(
    () => new Set(catalog.map((item) => item.id.toLowerCase())),
    [catalog],
  )

  const availableClis = useMemo(() => {
    return (cliQuery.data?.clis ?? []).filter((c) => !catalogAgentIds.has(c.toLowerCase()))
  }, [cliQuery.data, catalogAgentIds])

  const availableCliModels = useMemo(() => {
    return (cliModelsQuery.data?.models ?? []).filter((m) => !catalogAgentIds.has(m.toLowerCase()))
  }, [cliModelsQuery.data, catalogAgentIds])

  const availableApiModels = useMemo(() => {
    const raw = modelsQuery.data?.data ?? []
    return raw.filter((m) => !catalogAgentIds.has(m.id.toLowerCase()))
  }, [modelsQuery.data, catalogAgentIds])

  useEffect(() => {
    if (!isOpen || !id) return
    const edit = loadAgentEdit(id)
    const catalogAgent = exampleRoleAgents(blueprintsQuery.data?.data ?? []).find(
      (item) => item.id === id,
    )
    setName(edit.name || catalogAgent?.name || id)
    setRole(edit.role || agentRole({ id, name: catalogAgent?.name, role: catalogAgent?.role }))
    setBlueprintId(edit.blueprintId || id)
    setLlmOverride(edit.llmOverride || '')
    setCliOverride(edit.cliOverride || '')
    setProfileOverride(edit.profileOverride || '')

    let cancelled = false
    ;(async () => {
      const settings = await fetchAgentSettings(id)
      if (!cancelled) setNewChatPerTask(settings.new_chat_per_task)
    })()
    return () => {
      cancelled = true
    }
  }, [isOpen, id, blueprintsQuery.data])

  const handleToggleNewChat = async (next: boolean) => {
    setNewChatPerTask(next)
    if (!id) return
    setSavingSettings(true)
    try {
      await saveAgentSettings(id, { new_chat_per_task: next })
    } finally {
      setSavingSettings(false)
    }
  }

  const persistBlueprint = (nextId: string) => {
    setBlueprintId(nextId)
    saveAgentEdit(id, { blueprintId: nextId })
  }

  const persistName = (next: string) => {
    setName(next)
    saveAgentEdit(id, { name: next })
  }

  const persistRole = (next: AgentRole) => {
    setRole(next)
    saveAgentEdit(id, { role: next })
  }

  const openBlueprintInSettings = () => {
    const assigned = assignedBlueprintId(id) || blueprintId || id
    onClose()
    openSettingsSheet({ section: 'blueprint', blueprintId: assigned })
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      placement="end"
      size="lg"
      className="flex min-h-0 flex-col"
    >
      <div
        id="os-agent-editor"
        className="space-y-4 max-h-[calc(100vh-12rem)] overflow-y-auto pr-1"
        data-agent-id={id || undefined}
      >
        <p className="text-sm text-base-content/70">
          This pane is only about this agent. Blueprint picks a catalog recipe
          for this seat — it is not Settings.
        </p>

        <Input
          label="Name"
          name="agent-name"
          value={name}
          onChange={(event) => persistName(event.target.value)}
          autoComplete="off"
          spellCheck={false}
        />

        <div className="form-control">
          <Select
            label="Role"
            name="agent-role"
            value={role}
            onChange={(event) => persistRole(event.target.value as AgentRole)}
          >
            {ROLE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
          <p className="text-xs text-base-content/70 mt-1" data-testid="role-explanation">
            {ROLE_BRIEFS[role] || ROLE_BRIEFS.default}
          </p>
        </div>

        <Select
          label="Blueprint"
          name="agent-blueprint"
          value={blueprintId}
          onChange={(event) => persistBlueprint(event.target.value)}
        >
          {catalog.length === 0 || !catalog.some((item) => item.id === (blueprintId || id)) ? (
            <option value={blueprintId || id}>{blueprintId || id || 'Loading…'}</option>
          ) : null}
          {catalog.map((item) => (
            <option key={item.id} value={item.id}>
              {catalogLabel(item)}
            </option>
          ))}
        </Select>

        {/* LLM Override Picker by Kind (REQ-124) */}
        {agentKind === 'remote' && (
          <div className="rounded-box border border-base-300 bg-base-200/40 p-3 opacity-60">
            <span className="text-sm font-semibold text-base-content/70">LLM override</span>
            <p className="text-xs text-base-content/60 mt-1">Remotes keep their own models</p>
          </div>
        )}

        {agentKind === 'cli' && (
          <div className="space-y-3 rounded-box border border-base-300 bg-base-200/40 p-3">
            <div>
              <span className="text-sm font-semibold text-base-content/80">LLM override</span>
              <p className="text-xs text-base-content/60 mt-0.5" data-testid="default-llm-label">
                Default would be: {availableClis[0] || 'CLI default'} / {availableCliModels[0] || 'default'}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text text-xs">CLI</span>
                </label>
                <select
                  aria-label="CLI override"
                  className="select select-bordered select-sm w-full"
                  value={cliOverride}
                  onChange={(e) => {
                    const nextCli = e.target.value
                    setCliOverride(nextCli)
                    saveAgentEdit(id, { cliOverride: nextCli, llmOverride })
                  }}
                >
                  <option value="">Default CLI</option>
                  {availableClis.map((cli) => (
                    <option key={cli} value={cli}>
                      {cli}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text text-xs">Model</span>
                </label>
                <select
                  aria-label="Model override"
                  className="select select-bordered select-sm w-full"
                  value={llmOverride}
                  onChange={(e) => {
                    const nextModel = e.target.value
                    setLlmOverride(nextModel)
                    saveAgentEdit(id, { cliOverride, llmOverride: nextModel })
                  }}
                >
                  <option value="">Default model</option>
                  {availableCliModels.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {agentKind === 'api' && (
          <div className="space-y-3 rounded-box border border-base-300 bg-base-200/40 p-3">
            <div>
              <span className="text-sm font-semibold text-base-content/80">LLM override</span>
              <p className="text-xs text-base-content/60 mt-0.5" data-testid="default-llm-label">
                Default would be:{' '}
                {llmProfilesQuery.data?.default_llm_profile || 'orchestration'}
                {availableApiModels.length > 0 ? ` / ${availableApiModels[0].id}` : ''}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text text-xs">API / LLM profile</span>
                </label>
                <select
                  aria-label="API profile override"
                  className="select select-bordered select-sm w-full"
                  value={profileOverride}
                  onChange={(e) => {
                    const nextProfile = e.target.value
                    setProfileOverride(nextProfile)
                    saveAgentEdit(id, { profileOverride: nextProfile, llmOverride })
                  }}
                >
                  <option value="">Default profile</option>
                  <option value="orchestration">User chat / orchestration</option>
                  <option value="auxiliary">Auxiliary (code summary)</option>
                  <option value="delegation">Delegation (design / coding)</option>
                  {(llmProfilesQuery.data?.profiles ?? [])
                    .filter((p) => !['orchestration', 'auxiliary', 'delegation'].includes(p.id))
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name || p.id}
                      </option>
                    ))}
                </select>
              </div>

              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text text-xs">Model</span>
                </label>
                <select
                  aria-label="Model override"
                  className="select select-bordered select-sm w-full"
                  value={llmOverride}
                  onChange={(e) => {
                    const nextModel = e.target.value
                    setLlmOverride(nextModel)
                    saveAgentEdit(id, { profileOverride, llmOverride: nextModel })
                  }}
                >
                  <option value="">Default model</option>
                  {availableApiModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.id}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        <div
          className="tooltip tooltip-bottom w-full text-left"
          data-tip={NEW_CHAT_PER_TASK_TOOLTIP}
        >
          <label
            htmlFor={toggleId}
            className="label cursor-pointer items-center justify-between gap-4 rounded-box border border-base-300 bg-base-200/60 px-4 py-3"
          >
            <span className="label-text text-base font-semibold">{NEW_CHAT_PER_TASK_LABEL}</span>
            <input
              id={toggleId}
              type="checkbox"
              className="toggle toggle-primary"
              role="switch"
              aria-label={NEW_CHAT_PER_TASK_LABEL}
              checked={newChatPerTask}
              disabled={!id || savingSettings}
              onChange={(event) => handleToggleNewChat(event.target.checked)}
            />
          </label>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={!id}
            onClick={openBlueprintInSettings}
          >
            Edit blueprint…
          </Button>
        </div>
      </div>

      <div className="modal-action mt-4">
        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
          Close
        </Button>
      </div>
    </Modal>
  )
}
