import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Plus, Server } from 'lucide-react'
import { Alert, Button, Input, useToast } from './DaisyUI'
import { fetchConfigSection, patchConfigSection } from '../lib/api'

export default function McpServersPane() {
  const { success, error: toastError } = useToast()
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: ['settings-mcp-servers'],
    queryFn: () => fetchConfigSection('mcpServers'),
    retry: 1,
  })
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')
  const [command, setCommand] = useState('')
  const [argsText, setArgsText] = useState('')
  const [envName, setEnvName] = useState('')

  const data = (query.data?.data || {}) as Record<string, { command?: string; args?: string[] }>
  const names = Object.keys(data)

  const addMutation = useMutation({
    mutationFn: () => {
      const args = argsText
        .split(',')
        .map((part) => part.trim())
        .filter(Boolean)
      const entry: Record<string, unknown> = { command: command.trim(), args }
      if (envName.trim()) {
        const envKey = envName.trim()
        entry.env = { [envKey]: `\${${envKey}}` }
      }
      return patchConfigSection('mcpServers', { upsert: { [name.trim()]: entry } })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['settings-mcp-servers'] })
      setAdding(false)
      setName('')
      setCommand('')
      setArgsText('')
      setEnvName('')
      success('MCP server saved', 'Stored in swarm_config.json mcpServers.')
    },
    onError: (err: Error) => {
      toastError('Could not save MCP server', err.message)
    },
  })

  const removeMutation = useMutation({
    mutationFn: (serverName: string) => patchConfigSection('mcpServers', { delete: [serverName] }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['settings-mcp-servers'] })
      success('MCP server removed', 'Dropped from swarm_config.json.')
    },
    onError: (err: Error) => {
      toastError('Could not remove MCP server', err.message)
    },
  })

  const handleAdd = (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim() || !command.trim()) return
    addMutation.mutate()
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-lg font-semibold">MCP servers</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Non-secret MCP topology in <code>mcpServers</code>. Auth env values are{' '}
          <code>${'{VAR}'}</code> only — never paste a token.
        </p>
      </div>

      {query.isPending ? (
        <p className="text-sm text-base-content/60">Loading MCP servers…</p>
      ) : query.isError ? (
        <Alert type="warning" icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">Could not load mcpServers from config.</span>
        </Alert>
      ) : names.length === 0 && !adding ? (
        <Alert type="info" icon={<Server className="h-5 w-5" />}>
          <span className="text-sm">No MCP servers in swarm_config yet.</span>
        </Alert>
      ) : (
        <ul className="space-y-2" aria-label="Configured MCP servers">
          {names.map((serverName) => (
            <li
              key={serverName}
              className="flex items-start justify-between gap-3 rounded-lg border border-base-300 bg-base-200/60 px-3 py-2"
            >
              <div className="min-w-0">
                <p className="font-mono text-sm">{serverName}</p>
                <p className="truncate text-xs text-base-content/60">
                  {data[serverName]?.command || '—'} {(data[serverName]?.args || []).join(' ')}
                </p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="xs"
                onClick={() => removeMutation.mutate(serverName)}
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
            name="mcp-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="filesystem"
            autoComplete="off"
            spellCheck={false}
          />
          <Input
            label="Command"
            name="mcp-command"
            value={command}
            onChange={(event) => setCommand(event.target.value)}
            placeholder="npx"
            autoComplete="off"
            spellCheck={false}
          />
          <Input
            label="Args (comma-separated)"
            name="mcp-args"
            value={argsText}
            onChange={(event) => setArgsText(event.target.value)}
            placeholder="-y, @modelcontextprotocol/server-filesystem"
            autoComplete="off"
            spellCheck={false}
          />
          <Input
            label="Secret env name (optional)"
            name="mcp-env"
            value={envName}
            onChange={(event) => setEnvName(event.target.value)}
            placeholder="BRAVE_API_KEY"
            autoComplete="off"
            spellCheck={false}
          />
          <div className="flex flex-wrap gap-2">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={!name.trim() || !command.trim() || addMutation.isPending}
            >
              Save MCP server
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setAdding(false)}>
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <Button type="button" variant="outline" size="sm" onClick={() => setAdding(true)}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add MCP server
        </Button>
      )}
    </div>
  )
}
