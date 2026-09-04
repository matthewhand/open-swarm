import { useState, useId, useMemo } from 'react'
import { Terminal, Bot, Globe, ArrowLeft, Plus, ExternalLink, Edit3 } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal, Button, Alert } from './DaisyUI'
import {
  createCustomBlueprint,
  updateCustomBlueprint,
  createRemote,
  fetchBlueprints,
  fetchCliAgents,
  fetchCustomBlueprints,
} from '../lib/api'
import { OPENMOUSBOT_LABEL } from '../lib/remotesCatalog'
import { loadAgentEdit, saveAgentEdit } from '../lib/agentEdits'

export type AgentKind = 'cli' | 'api' | 'remote'

export interface AddAgentWizardProps {
  isOpen: boolean
  onClose: () => void
  onCreated?: (agent: { id: string; name: string; kind: AgentKind }) => void
  onSelectAgent?: (agentId: string) => void
}

export function isValidFolderPath(path: string): boolean {
  if (!path.trim()) return true
  if (/[\0*?"<>|\r\n]/.test(path)) return false
  return true
}

export interface ManageAgentItem {
  id: string
  name: string
  command?: string
  folder?: string
  description?: string
  prompt?: string
  isCustom: boolean
}

/**
 * REQ-109 / REQ-164 / REQ-165 / REQ-167: Add agent popup wizard.
 *
 * - Step 1: Choose agent kind (CLI, API, Remote with OpenMousBot copy).
 * - Step 2 (CLI / API): Manage existing agents of that kind (list + edit + open + add new).
 * - Step 3 / Configure: Create new agent or edit existing agent.
 * - Overlay only: chat stays mounted (#364). Esc / backdrop cancels without creating.
 */
export default function AddAgentWizard({
  isOpen,
  onClose,
  onCreated,
  onSelectAgent,
}: AddAgentWizardProps) {
  const queryClient = useQueryClient()
  const titleId = useId()

  const [step, setStep] = useState<'select_kind' | 'manage' | 'configure'>('select_kind')
  const [selectedKind, setSelectedKind] = useState<AgentKind>('cli')
  const [mode, setMode] = useState<'create' | 'edit'>('create')
  const [editingAgentId, setEditingAgentId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // CLI fields
  const [cliName, setCliName] = useState('')
  const [cliCommand, setCliCommand] = useState('')
  const [cliFolder, setCliFolder] = useState('')
  const [cliDescription, setCliDescription] = useState('')
  const [folderError, setFolderError] = useState<string | null>(null)

  // API fields
  const [apiName, setApiName] = useState('')
  const [apiDescription, setApiDescription] = useState('')
  const [apiPrompt, setApiPrompt] = useState('')

  // Remote fields
  const [remoteKind, setRemoteKind] = useState<'omb' | 'generic'>('omb')
  const [remoteBaseUrl, setRemoteBaseUrl] = useState('')
  const [remoteApiKey, setRemoteApiKey] = useState('')

  // Queries for existing agents
  const blueprintsQuery = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
    enabled: isOpen,
    retry: 1,
  })

  const customBlueprintsQuery = useQuery({
    queryKey: ['custom-blueprints'],
    queryFn: fetchCustomBlueprints,
    enabled: isOpen,
    retry: 1,
  })

  const cliQuery = useQuery({
    queryKey: ['cli-agents'],
    queryFn: fetchCliAgents,
    enabled: isOpen,
    retry: 1,
  })

  const resetFormFields = () => {
    setError(null)
    setFolderError(null)
    setSubmitting(false)
    setCliName('')
    setCliCommand('')
    setCliFolder('')
    setCliDescription('')
    setApiName('')
    setApiDescription('')
    setApiPrompt('')
    setRemoteKind('omb')
    setRemoteBaseUrl('')
    setRemoteApiKey('')
    setEditingAgentId(null)
  }

  const handleClose = () => {
    resetFormFields()
    setStep('select_kind')
    setSelectedKind('cli')
    setMode('create')
    onClose()
  }

  const handleSelectKind = (kind: AgentKind) => {
    setSelectedKind(kind)
    setError(null)
    if (kind === 'remote') {
      setMode('create')
      setStep('configure')
    } else {
      setStep('manage')
    }
  }

  // Aggregate CLI agents
  const cliAgents = useMemo<ManageAgentItem[]>(() => {
    const list: ManageAgentItem[] = []
    const seen = new Set<string>()

    const customList = customBlueprintsQuery.data?.data ?? []
    for (const item of customList) {
      if (item.category === 'cli' || item.tags?.includes('cli')) {
        const edits = loadAgentEdit(item.id)
        const name = edits.name || item.name || item.id
        const commandMatch = item.code?.match(/# Command:\s*(.*)/)
        const folderMatch = item.code?.match(/# Folder:\s*(.*)/)
        const command =
          edits.command || (commandMatch ? commandMatch[1].trim() : '') || item.description || ''
        const folder = edits.folder || (folderMatch ? folderMatch[1].trim() : '')
        seen.add(item.id)
        list.push({
          id: item.id,
          name,
          command,
          folder,
          description: item.description,
          isCustom: true,
        })
      }
    }

    const rail = cliQuery.data?.rail ?? []
    for (const item of rail) {
      if (seen.has(item.id)) continue
      const edits = loadAgentEdit(item.id)
      const name = edits.name || item.name || item.id
      const command = edits.command || item.cli || ''
      const folder = edits.folder || ''
      seen.add(item.id)
      list.push({
        id: item.id,
        name,
        command: command || (item.installed ? 'installed' : 'not on PATH'),
        folder,
        description: item.description,
        isCustom: false,
      })
    }

    const catalog = blueprintsQuery.data?.data ?? []
    for (const item of catalog) {
      if (seen.has(item.id)) continue
      if (item.category === 'cli' || item.tags?.includes('cli')) {
        const edits = loadAgentEdit(item.id)
        const name = edits.name || item.name || item.id
        const command = edits.command || item.description || ''
        const folder = edits.folder || ''
        seen.add(item.id)
        list.push({
          id: item.id,
          name,
          command,
          folder,
          description: item.description,
          isCustom: false,
        })
      }
    }

    return list
  }, [customBlueprintsQuery.data, cliQuery.data, blueprintsQuery.data])

  // Aggregate API agents
  const apiAgents = useMemo<ManageAgentItem[]>(() => {
    const list: ManageAgentItem[] = []
    const seen = new Set<string>()

    const customList = customBlueprintsQuery.data?.data ?? []
    for (const item of customList) {
      if (item.category === 'cli' || item.tags?.includes('cli')) continue
      const edits = loadAgentEdit(item.id)
      const name = edits.name || item.name || item.id
      seen.add(item.id)
      list.push({
        id: item.id,
        name,
        description: item.description || '',
        prompt: item.code || '',
        isCustom: true,
      })
    }

    const catalog = blueprintsQuery.data?.data ?? []
    for (const item of catalog) {
      if (seen.has(item.id)) continue
      if (item.category === 'cli' || item.tags?.includes('cli')) continue
      const edits = loadAgentEdit(item.id)
      const name = edits.name || item.name || item.id
      seen.add(item.id)
      list.push({
        id: item.id,
        name,
        description: item.description || '',
        isCustom: false,
      })
    }

    return list
  }, [customBlueprintsQuery.data, blueprintsQuery.data])

  const handleStartAddNew = () => {
    resetFormFields()
    setMode('create')
    setStep('configure')
  }

  const handleStartEdit = (agent: ManageAgentItem) => {
    setError(null)
    setFolderError(null)
    setEditingAgentId(agent.id)
    setMode('edit')
    if (selectedKind === 'cli') {
      setCliName(agent.name)
      setCliCommand(agent.command || '')
      setCliFolder(agent.folder || '')
      setCliDescription(agent.description || '')
    } else if (selectedKind === 'api') {
      setApiName(agent.name)
      setApiDescription(agent.description || '')
      setApiPrompt(agent.prompt || '')
    }
    setStep('configure')
  }

  const handleOpenAgent = (agentId: string) => {
    if (onSelectAgent) {
      onSelectAgent(agentId)
    } else if (typeof window !== 'undefined') {
      window.location.href = `/chat?blueprint=${encodeURIComponent(agentId)}`
    }
    handleClose()
  }

  const handleCancelConfigure = () => {
    if (selectedKind === 'remote') {
      handleClose()
    } else {
      resetFormFields()
      setStep('manage')
    }
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)

    if (selectedKind === 'cli' && cliFolder.trim() && !isValidFolderPath(cliFolder)) {
      setFolderError('Please enter a valid directory path (e.g. /path/to/dir or ./dir)')
      return
    }

    setSubmitting(true)

    try {
      if (selectedKind === 'cli') {
        const name = cliName.trim()
        const command = cliCommand.trim()
        const folder = cliFolder.trim()
        const description = cliDescription.trim()
        if (!name) throw new Error('Agent name is required')
        if (!command) throw new Error('CLI command or binary is required')

        const folderComment = folder ? `# Folder: ${folder}\n` : ''
        const code = `# CLI agent: ${name}\n# Command: ${command}\n${folderComment}`

        if (mode === 'create') {
          const created = await createCustomBlueprint({
            name,
            description: description || `CLI: ${command}`,
            category: 'cli',
            code,
            tags: ['cli'],
          })

          saveAgentEdit(created.id, {
            name,
            command,
            folder,
          })

          await queryClient.invalidateQueries({ queryKey: ['blueprints'] })
          await queryClient.invalidateQueries({ queryKey: ['custom-blueprints'] })
          await queryClient.invalidateQueries({ queryKey: ['cli-agents'] })
          onCreated?.({ id: created.id, name: created.name, kind: 'cli' })
          handleClose()
        } else if (mode === 'edit' && editingAgentId) {
          saveAgentEdit(editingAgentId, {
            name,
            command,
            folder,
          })

          try {
            await updateCustomBlueprint(editingAgentId, {
              name,
              description: description || `CLI: ${command}`,
              code,
            })
          } catch {
            // Local edits already saved via saveAgentEdit
          }

          await queryClient.invalidateQueries({ queryKey: ['blueprints'] })
          await queryClient.invalidateQueries({ queryKey: ['custom-blueprints'] })
          await queryClient.invalidateQueries({ queryKey: ['cli-agents'] })
          resetFormFields()
          setStep('manage')
        }
      } else if (selectedKind === 'api') {
        const name = apiName.trim()
        const description = apiDescription.trim()
        const prompt = apiPrompt.trim()
        if (!name) throw new Error('Agent name is required')

        if (mode === 'create') {
          const created = await createCustomBlueprint({
            name,
            description,
            category: 'ai_assistants',
            code: prompt || `# API Assistant: ${name}\n`,
            tags: ['api'],
          })

          saveAgentEdit(created.id, { name })

          await queryClient.invalidateQueries({ queryKey: ['blueprints'] })
          await queryClient.invalidateQueries({ queryKey: ['custom-blueprints'] })
          onCreated?.({ id: created.id, name: created.name, kind: 'api' })
          handleClose()
        } else if (mode === 'edit' && editingAgentId) {
          saveAgentEdit(editingAgentId, { name })

          try {
            await updateCustomBlueprint(editingAgentId, {
              name,
              description,
              code: prompt || `# API Assistant: ${name}\n`,
            })
          } catch {
            // Local edits already saved via saveAgentEdit
          }

          await queryClient.invalidateQueries({ queryKey: ['blueprints'] })
          await queryClient.invalidateQueries({ queryKey: ['custom-blueprints'] })
          resetFormFields()
          setStep('manage')
        }
      } else if (selectedKind === 'remote') {
        const baseUrl = remoteBaseUrl.trim()
        if (!baseUrl) throw new Error('Base URL is required')

        const created = await createRemote({
          kind: remoteKind === 'omb' ? 'omb' : 'remote',
          base_url: baseUrl,
          ...(remoteApiKey.trim() ? { api_key: remoteApiKey.trim() } : {}),
        })

        await queryClient.invalidateQueries({ queryKey: ['configured-remotes'] })
        await queryClient.invalidateQueries({ queryKey: ['settings-remotes'] })
        onCreated?.({
          id: created.id,
          name: remoteKind === 'omb' ? OPENMOUSBOT_LABEL : created.id,
          kind: 'remote',
        })
        handleClose()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save agent')
    } finally {
      setSubmitting(false)
    }
  }

  const currentAgents = selectedKind === 'cli' ? cliAgents : apiAgents

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      size="md"
      placement="middle"
      aria-label="Add agent wizard"
    >
      <div className="space-y-4" data-testid="add-agent-wizard">
        <div className="flex items-center justify-between border-b border-base-300 pb-3">
          <div className="flex items-center gap-2">
            {step !== 'select_kind' ? (
              <button
                type="button"
                className="btn btn-ghost btn-sm btn-circle"
                aria-label="Back"
                onClick={() => {
                  setError(null)
                  if (step === 'configure' && selectedKind !== 'remote') {
                    setStep('manage')
                  } else {
                    setStep('select_kind')
                  }
                }}
              >
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              </button>
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Plus className="h-4 w-4" aria-hidden="true" />
              </div>
            )}
            <div>
              <h3 id={titleId} className="text-base font-semibold">
                {step === 'select_kind'
                  ? 'Add Agent'
                  : step === 'manage'
                  ? selectedKind === 'cli'
                    ? 'Manage CLI Agents'
                    : 'Manage API Agents'
                  : mode === 'edit'
                  ? `Edit ${selectedKind === 'cli' ? 'CLI' : 'API'} Agent`
                  : selectedKind === 'cli'
                  ? 'Configure CLI Agent'
                  : selectedKind === 'api'
                  ? 'Configure API Agent'
                  : 'Configure Remote Agent'}
              </h3>
              <p className="text-xs text-base-content/60">
                {step === 'select_kind'
                  ? 'Choose the type of agent to manage or create'
                  : step === 'manage'
                  ? selectedKind === 'cli'
                    ? 'Launch, edit, or create local command-line agents'
                    : 'Launch, edit, or create API assistants'
                  : selectedKind === 'cli'
                  ? 'Connect a local command-line executable or script'
                  : selectedKind === 'api'
                  ? 'Create an autonomous API recipe or assistant'
                  : `Connect an external ${OPENMOUSBOT_LABEL} or HTTP worker`}
              </p>
            </div>
          </div>

          {step === 'manage' && (
            <Button
              type="button"
              variant="outline"
              size="xs"
              onClick={handleStartAddNew}
              data-testid="add-new-agent-btn"
            >
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              Add new
            </Button>
          )}
        </div>

        {error ? (
          <Alert type="error" className="py-2 text-xs">
            {error}
          </Alert>
        ) : null}

        {step === 'select_kind' ? (
          <div
            className="grid grid-cols-1 gap-2.5 sm:grid-cols-3"
            role="radiogroup"
            aria-label="Agent kinds"
          >
            {/* CLI */}
            <button
              type="button"
              className="flex flex-col items-start gap-2 rounded-xl border border-base-300 bg-base-100 p-3.5 text-left transition hover:border-primary hover:bg-base-200/50"
              onClick={() => handleSelectKind('cli')}
              data-testid="kind-option-cli"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-500">
                <Terminal className="h-4 w-4" aria-hidden="true" />
              </div>
              <div>
                <span className="block text-sm font-semibold">CLI</span>
                <span className="mt-0.5 block text-xs text-base-content/60 leading-tight">
                  Run command-line binaries or local terminal tools
                </span>
              </div>
            </button>

            {/* API */}
            <button
              type="button"
              className="flex flex-col items-start gap-2 rounded-xl border border-base-300 bg-base-100 p-3.5 text-left transition hover:border-primary hover:bg-base-200/50"
              onClick={() => handleSelectKind('api')}
              data-testid="kind-option-api"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/10 text-sky-500">
                <Bot className="h-4 w-4" aria-hidden="true" />
              </div>
              <div>
                <span className="block text-sm font-semibold">API</span>
                <span className="mt-0.5 block text-xs text-base-content/60 leading-tight">
                  Autonomous assistant with custom prompt and code
                </span>
              </div>
            </button>

            {/* Remote */}
            <button
              type="button"
              className="flex flex-col items-start gap-2 rounded-xl border border-base-300 bg-base-100 p-3.5 text-left transition hover:border-primary hover:bg-base-200/50"
              onClick={() => handleSelectKind('remote')}
              data-testid="kind-option-remote"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10 text-purple-500">
                <Globe className="h-4 w-4" aria-hidden="true" />
              </div>
              <div>
                <span className="block text-sm font-semibold">Remote</span>
                <span className="mt-0.5 block text-xs text-base-content/60 leading-tight">
                  Connect {OPENMOUSBOT_LABEL} or HTTP worker
                </span>
              </div>
            </button>
          </div>
        ) : step === 'manage' ? (
          <div className="space-y-3" data-testid="manage-agent-surface">
            {currentAgents.length === 0 ? (
              <div
                className="rounded-xl border border-dashed border-base-300 py-8 text-center"
                data-testid="empty-manage-state"
              >
                <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-base-200 text-base-content/50">
                  {selectedKind === 'cli' ? (
                    <Terminal className="h-5 w-5" />
                  ) : (
                    <Bot className="h-5 w-5" />
                  )}
                </div>
                <p className="mt-2 text-sm font-medium">
                  {selectedKind === 'cli' ? 'No CLI agents yet' : 'No API agents yet'}
                </p>
                <p className="mt-1 text-xs text-base-content/60">
                  Get started by creating your first {selectedKind === 'cli' ? 'CLI' : 'API'} agent.
                </p>
                <Button
                  type="button"
                  variant="primary"
                  size="sm"
                  className="mt-4"
                  onClick={handleStartAddNew}
                  data-testid="empty-add-btn"
                >
                  Add {selectedKind === 'cli' ? 'CLI' : 'API'} Agent
                </Button>
              </div>
            ) : (
              <div className="max-h-80 overflow-y-auto space-y-2 pr-1" data-testid="manage-agent-list">
                {currentAgents.map((agent) => (
                  <div
                    key={agent.id}
                    className="flex items-center justify-between rounded-lg border border-base-300 bg-base-100 p-2.5 hover:bg-base-200/40"
                    data-testid={`agent-row-${agent.id}`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div
                        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${
                          selectedKind === 'cli'
                            ? 'bg-emerald-500/10 text-emerald-500'
                            : 'bg-sky-500/10 text-sky-500'
                        }`}
                      >
                        {selectedKind === 'cli' ? (
                          <Terminal className="h-3.5 w-3.5" />
                        ) : (
                          <Bot className="h-3.5 w-3.5" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-semibold truncate leading-tight">{agent.name}</p>
                        <p className="text-[11px] text-base-content/60 truncate font-mono mt-0.5">
                          {selectedKind === 'cli'
                            ? agent.command || 'CLI'
                            : agent.description || 'API Assistant'}
                          {agent.folder ? ` · ${agent.folder}` : ''}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0 ml-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="xs"
                        onClick={() => handleStartEdit(agent)}
                        data-testid={`edit-agent-${agent.id}`}
                        aria-label={`Edit ${agent.name}`}
                      >
                        <Edit3 className="h-3.5 w-3.5" aria-hidden="true" />
                        Edit
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="xs"
                        onClick={() => handleOpenAgent(agent.id)}
                        data-testid={`open-agent-${agent.id}`}
                        aria-label={`Open ${agent.name}`}
                      >
                        <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                        Open
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3.5" data-testid="add-agent-form">
            {selectedKind === 'cli' ? (
              <>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-base-content/80">
                    Agent Name <span className="text-error">*</span>
                  </label>
                  <input
                    type="text"
                    className="input input-sm input-bordered w-full"
                    placeholder="e.g. Claude Code CLI"
                    value={cliName}
                    onChange={(e) => setCliName(e.target.value)}
                    required
                    autoFocus
                    aria-label="Agent name"
                    data-testid="input-cli-name"
                  />
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-base-content/80">
                    Command or Executable <span className="text-error">*</span>
                  </label>
                  <input
                    type="text"
                    className="input input-sm input-bordered w-full font-mono text-xs"
                    placeholder="e.g. claude, bash, python"
                    value={cliCommand}
                    onChange={(e) => setCliCommand(e.target.value)}
                    required
                    aria-label="CLI command"
                    data-testid="input-cli-command"
                  />
                </div>
                {/* REQ-167: CLI Folder workspace field */}
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-base-content/80">
                    Folder <span className="text-xs font-normal text-base-content/60">(optional)</span>
                  </label>
                  <input
                    type="text"
                    className={`input input-sm input-bordered w-full font-mono text-xs ${
                      folderError ? 'input-error' : ''
                    }`}
                    placeholder="/path/to/working/directory or ./project"
                    value={cliFolder}
                    onChange={(e) => {
                      const val = e.target.value
                      setCliFolder(val)
                      if (val && !isValidFolderPath(val)) {
                        setFolderError(
                          'Please enter a valid directory path (e.g. /path/to/dir or ./dir)',
                        )
                      } else {
                        setFolderError(null)
                      }
                    }}
                    aria-label="Folder"
                    data-testid="input-cli-folder"
                  />
                  <span className="block text-[11px] text-base-content/60">
                    Working directory for this CLI agent
                  </span>
                  {folderError ? (
                    <span className="block text-xs text-error" data-testid="folder-error">
                      {folderError}
                    </span>
                  ) : null}
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-base-content/80">
                    Description (optional)
                  </label>
                  <input
                    type="text"
                    className="input input-sm input-bordered w-full text-xs"
                    placeholder="Brief description of what this agent does"
                    value={cliDescription}
                    onChange={(e) => setCliDescription(e.target.value)}
                    aria-label="Description"
                  />
                </div>
              </>
            ) : null}

            {selectedKind === 'api' ? (
              <>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-base-content/80">
                    Agent Name <span className="text-error">*</span>
                  </label>
                  <input
                    type="text"
                    className="input input-sm input-bordered w-full"
                    placeholder="e.g. Research Analyst"
                    value={apiName}
                    onChange={(e) => setApiName(e.target.value)}
                    required
                    autoFocus
                    aria-label="Agent name"
                    data-testid="input-api-name"
                  />
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-base-content/80">
                    Description (optional)
                  </label>
                  <input
                    type="text"
                    className="input input-sm input-bordered w-full text-xs"
                    placeholder="e.g. Specialized in technical analysis and summaries"
                    value={apiDescription}
                    onChange={(e) => setApiDescription(e.target.value)}
                    aria-label="Description"
                  />
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-base-content/80">
                    System Instructions / Prompt
                  </label>
                  <textarea
                    className="textarea textarea-sm textarea-bordered w-full font-mono text-xs"
                    rows={3}
                    placeholder="You are an expert AI assistant..."
                    value={apiPrompt}
                    onChange={(e) => setApiPrompt(e.target.value)}
                    aria-label="System prompt"
                    data-testid="input-api-prompt"
                  />
                </div>
              </>
            ) : null}

            {selectedKind === 'remote' ? (
              <>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-base-content/80">
                    Remote Type <span className="text-error">*</span>
                  </label>
                  <select
                    className="select select-sm select-bordered w-full"
                    value={remoteKind}
                    onChange={(e) => setRemoteKind(e.target.value as 'omb' | 'generic')}
                    aria-label="Remote type"
                    data-testid="select-remote-kind"
                  >
                    <option value="omb">{OPENMOUSBOT_LABEL}</option>
                    <option value="generic">Generic Remote Agent</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-base-content/80">
                    Base URL <span className="text-error">*</span>
                  </label>
                  <input
                    type="url"
                    className="input input-sm input-bordered w-full font-mono text-xs"
                    placeholder="http://localhost:8000"
                    value={remoteBaseUrl}
                    onChange={(e) => setRemoteBaseUrl(e.target.value)}
                    required
                    autoFocus
                    aria-label="Base URL"
                    data-testid="input-remote-url"
                  />
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-base-content/80">
                    API Key / Token (optional)
                  </label>
                  <input
                    type="password"
                    className="input input-sm input-bordered w-full text-xs"
                    placeholder="Optional authorization token"
                    value={remoteApiKey}
                    onChange={(e) => setRemoteApiKey(e.target.value)}
                    aria-label="API Key"
                    data-testid="input-remote-key"
                  />
                </div>
              </>
            ) : null}

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleCancelConfigure}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                loading={submitting}
                disabled={Boolean(folderError)}
                data-testid="submit-create-agent"
              >
                {mode === 'edit' ? 'Save Changes' : 'Create Agent'}
              </Button>
            </div>
          </form>
        )}
      </div>
    </Modal>
  )
}
