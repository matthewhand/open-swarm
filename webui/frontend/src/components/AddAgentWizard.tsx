import { useState, useId } from 'react'
import { Terminal, Bot, Globe, ArrowLeft, Plus } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { Modal, Button, Alert } from './DaisyUI'
import { createCustomBlueprint, createRemote } from '../lib/api'
import { OPENMOUSBOT_LABEL } from '../lib/remotesCatalog'

export type AgentKind = 'cli' | 'api' | 'remote'

export interface AddAgentWizardProps {
  isOpen: boolean
  onClose: () => void
  onCreated?: (agent: { id: string; name: string; kind: AgentKind }) => void
}

/**
 * REQ-109: Add agent popup wizard (CLI | API | Remote) opened beside favourites.
 *
 * - Step 1: Choose agent kind (CLI, API, Remote with OpenMousBot copy).
 * - Step 2: Configure and create agent.
 * - Overlay only: chat stays mounted (#364). Esc / backdrop cancels without creating.
 */
export default function AddAgentWizard({
  isOpen,
  onClose,
  onCreated,
}: AddAgentWizardProps) {
  const queryClient = useQueryClient()
  const titleId = useId()

  const [step, setStep] = useState<'select_kind' | 'configure'>('select_kind')
  const [selectedKind, setSelectedKind] = useState<AgentKind>('cli')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // CLI fields
  const [cliName, setCliName] = useState('')
  const [cliCommand, setCliCommand] = useState('')
  const [cliDescription, setCliDescription] = useState('')

  // API fields
  const [apiName, setApiName] = useState('')
  const [apiDescription, setApiDescription] = useState('')
  const [apiPrompt, setApiPrompt] = useState('')

  // Remote fields
  const [remoteKind, setRemoteKind] = useState<'omb' | 'generic'>('omb')
  const [remoteBaseUrl, setRemoteBaseUrl] = useState('')
  const [remoteApiKey, setRemoteApiKey] = useState('')

  const handleClose = () => {
    // Reset state and close
    setStep('select_kind')
    setSelectedKind('cli')
    setError(null)
    setSubmitting(false)
    setCliName('')
    setCliCommand('')
    setCliDescription('')
    setApiName('')
    setApiDescription('')
    setApiPrompt('')
    setRemoteKind('omb')
    setRemoteBaseUrl('')
    setRemoteApiKey('')
    onClose()
  }

  const handleSelectKind = (kind: AgentKind) => {
    setSelectedKind(kind)
    setError(null)
    setStep('configure')
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      if (selectedKind === 'cli') {
        const name = cliName.trim()
        const command = cliCommand.trim()
        if (!name) throw new Error('Agent name is required')
        if (!command) throw new Error('CLI command or binary is required')

        const created = await createCustomBlueprint({
          name,
          description: cliDescription.trim() || `CLI: ${command}`,
          category: 'cli',
          code: `# CLI agent: ${name}\n# Command: ${command}\n`,
          tags: ['cli'],
        })

        await queryClient.invalidateQueries({ queryKey: ['blueprints'] })
        await queryClient.invalidateQueries({ queryKey: ['cli-agents'] })
        onCreated?.({ id: created.id, name: created.name, kind: 'cli' })
        handleClose()
      } else if (selectedKind === 'api') {
        const name = apiName.trim()
        if (!name) throw new Error('Agent name is required')

        const created = await createCustomBlueprint({
          name,
          description: apiDescription.trim(),
          category: 'ai_assistants',
          code: apiPrompt.trim() || `# API Assistant: ${name}\n`,
          tags: ['api'],
        })

        await queryClient.invalidateQueries({ queryKey: ['blueprints'] })
        onCreated?.({ id: created.id, name: created.name, kind: 'api' })
        handleClose()
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
      setError(err instanceof Error ? err.message : 'Failed to create agent')
    } finally {
      setSubmitting(false)
    }
  }

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
            {step === 'configure' ? (
              <button
                type="button"
                className="btn btn-ghost btn-sm btn-circle"
                aria-label="Back to kind selection"
                onClick={() => {
                  setError(null)
                  setStep('select_kind')
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
                  : selectedKind === 'cli'
                  ? 'Configure CLI Agent'
                  : selectedKind === 'api'
                  ? 'Configure API Agent'
                  : 'Configure Remote Agent'}
              </h3>
              <p className="text-xs text-base-content/60">
                {step === 'select_kind'
                  ? 'Choose the type of agent to create'
                  : selectedKind === 'cli'
                  ? 'Connect a local command-line executable or script'
                  : selectedKind === 'api'
                  ? 'Create an autonomous API recipe or assistant'
                  : `Connect an external ${OPENMOUSBOT_LABEL} or HTTP worker`}
              </p>
            </div>
          </div>
        </div>

        {error ? (
          <Alert type="error" className="py-2 text-xs">
            {error}
          </Alert>
        ) : null}

        {step === 'select_kind' ? (
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3" role="radiogroup" aria-label="Agent kinds">
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
              <Button type="button" variant="ghost" size="sm" onClick={handleClose} disabled={submitting}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" loading={submitting} data-testid="submit-create-agent">
                Create Agent
              </Button>
            </div>
          </form>
        )}
      </div>
    </Modal>
  )
}
