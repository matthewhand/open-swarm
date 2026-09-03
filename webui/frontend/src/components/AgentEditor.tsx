import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Input, Modal, Select } from './DaisyUI'
import { fetchBlueprints, fetchModels, type AgentRole, type Blueprint } from '../lib/api'
import {
  assignedBlueprintId,
  loadAgentEdit,
  saveAgentEdit,
} from '../lib/agentEdits'
import { agentRole, exampleRoleAgents } from '../lib/agentRoles'
import { agentLabel, catalogLabel } from '../lib/supportAgent'
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
 * Agent-scoped editor overlay (REQ-58).
 *
 * Name, role, which catalog blueprint this seat uses, optional per-agent LLM
 * override. Not Settings: no Remotes, System, CLI catalog, or other instance
 * chrome. Chat stays mounted underneath.
 */
export default function AgentEditor({ isOpen, onClose, agentId }: AgentEditorProps) {
  const id = agentId || ''
  const [name, setName] = useState('')
  const [role, setRole] = useState<AgentRole>('default')
  const [blueprintId, setBlueprintId] = useState('')
  const [llmOverride, setLlmOverride] = useState('')

  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
    enabled: isOpen,
    retry: 1,
  })
  const modelsQuery = useQuery({
    queryKey: ['settings-llm-profiles'],
    queryFn: fetchModels,
    enabled: isOpen,
    retry: 1,
  })

  const catalog = useMemo(
    () => exampleRoleAgents(blueprintsQuery.data?.data ?? EMPTY_BLUEPRINTS),
    [blueprintsQuery.data],
  )
  const models = modelsQuery.data?.data ?? []
  const agent = catalog.find((item) => item.id === id)
  const catalogName = agent ? agentLabel({ id: agent.id, name: agent.name }) : id
  const title = id ? `Edit ${catalogName}` : 'Edit agent'

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
  }, [isOpen, id, blueprintsQuery.data])

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

  const persistLlm = (next: string) => {
    setLlmOverride(next)
    saveAgentEdit(id, { llmOverride: next })
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
      <div id="os-agent-editor" className="space-y-4" data-agent-id={id || undefined}>
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

        {models.length > 0 ? (
          <Select
            label="LLM override"
            name="agent-llm-override"
            value={llmOverride}
            onChange={(event) => persistLlm(event.target.value)}
          >
            <option value="">Default</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.id}
              </option>
            ))}
          </Select>
        ) : null}

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
