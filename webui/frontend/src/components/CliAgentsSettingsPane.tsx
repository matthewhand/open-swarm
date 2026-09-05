import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Plus, Server } from 'lucide-react'
import { Alert, Button, Input, useToast } from './DaisyUI'
import { fetchConfigSection, patchConfigSection } from '../lib/api'

export default function CliAgentsSettingsPane() {
  const { success, error: toastError } = useToast()
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: ['settings-cli-agents'],
    queryFn: () => fetchConfigSection('cli_agents'),
    retry: 1,
  })
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')
  const [cmdText, setCmdText] = useState('')

  const data = (query.data?.data || {}) as Record<string, { cmd?: string[] }>
  const names = Object.keys(data)

  const addMutation = useMutation({
    mutationFn: () => {
      const cmd = cmdText
        .split(',')
        .map((part) => part.trim())
        .filter(Boolean)
      return patchConfigSection('cli_agents', { upsert: { [name.trim()]: { cmd } } })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['settings-cli-agents'] })
      setAdding(false)
      setName('')
      setCmdText('')
      success('CLI agent saved', 'Stored in swarm_config.json cli_agents.')
    },
    onError: (err: Error) => {
      toastError('Could not save CLI agent', err.message)
    },
  })

  const removeMutation = useMutation({
    mutationFn: (cliName: string) => patchConfigSection('cli_agents', { delete: [cliName] }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['settings-cli-agents'] })
      success('CLI agent removed', 'Dropped from swarm_config.json.')
    },
    onError: (err: Error) => {
      toastError('Could not remove CLI agent', err.message)
    },
  })

  const handleAdd = (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim() || !cmdText.trim()) return
    addMutation.mutate()
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-lg font-semibold">CLI agents</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Wrapped CLIs in <code>cli_agents</code>. Each CLI keeps its own auth — Open Swarm
          never stores those secrets.
        </p>
      </div>

      {query.isPending ? (
        <p className="text-sm text-base-content/60">Loading CLI agents…</p>
      ) : query.isError ? (
        <Alert type="warning" icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">Could not load cli_agents from config.</span>
        </Alert>
      ) : names.length === 0 && !adding ? (
        <Alert type="info" icon={<Server className="h-5 w-5" />}>
          <span className="text-sm">No CLI agents in swarm_config yet.</span>
        </Alert>
      ) : (
        <ul className="space-y-2" aria-label="Configured CLI agents">
          {names.map((cliName) => (
            <li
              key={cliName}
              className="flex items-start justify-between gap-3 rounded-lg border border-base-300 bg-base-200/60 px-3 py-2"
            >
              <div className="min-w-0">
                <p className="font-mono text-sm">{cliName}</p>
                <p className="truncate text-xs text-base-content/60">
                  {(data[cliName]?.cmd || []).join(' ') || '—'}
                </p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="xs"
                onClick={() => removeMutation.mutate(cliName)}
                disabled={removeMutation.isPending}
              >
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}

      {adding ? (
        <form className="space-y-3 rounded-box border border-base-300 p-3" onSubmit={handleAdd}>
          <Input
            label="Name"
            name="cli-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="grok"
            autoComplete="off"
            spellCheck={false}
          />
          <Input
            label="Command (comma-separated)"
            name="cli-cmd"
            value={cmdText}
            onChange={(event) => setCmdText(event.target.value)}
            placeholder="grok"
            autoComplete="off"
            spellCheck={false}
          />
          <div className="flex flex-wrap gap-2">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={!name.trim() || !cmdText.trim() || addMutation.isPending}
            >
              Save CLI agent
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setAdding(false)}>
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <Button type="button" variant="outline" size="sm" onClick={() => setAdding(true)}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add CLI agent
        </Button>
      )}
    </div>
  )
}
