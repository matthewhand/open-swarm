import { useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Plus, Server } from 'lucide-react'
import { Alert, Button, Input, Select, Textarea } from './DaisyUI'
import {
  addRemote,
  fetchRemotes,
  operateRemote,
  probeRemoteHealth,
  type RemoteConnection,
  type RemoteHealthResult,
  type RemoteKind,
  type RemoteOperateResult,
} from '../lib/api'

const REMOTES_QUERY_KEY = ['settings-remotes'] as const

export default function RemotesSettings() {
  const queryClient = useQueryClient()
  const [adding, setAdding] = useState(false)

  const remotesQuery = useQuery({
    queryKey: REMOTES_QUERY_KEY,
    queryFn: fetchRemotes,
    retry: false,
  })

  const remotes = remotesQuery.data?.data ?? []
  const kinds = remotesQuery.data?.kinds ?? []

  return (
    <section aria-labelledby="os-remotes-heading" className="space-y-4">
      <div>
        <h4 id="os-remotes-heading" className="text-lg font-semibold">
          Remotes
        </h4>
        <p className="mt-1 text-sm text-base-content/70">
          Opt-in harness connections. Add a kind, then health / list / send
          through that product&apos;s API. Auth is an env-var name only.
        </p>
      </div>

      {remotesQuery.isPending ? (
        <p className="text-sm text-base-content/60">Loading remotes…</p>
      ) : remotesQuery.isError ? (
        <Alert type="warning" icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">Could not load remotes. Retry from Settings.</span>
        </Alert>
      ) : remotes.length === 0 && !adding ? (
        <EmptyRemotes onAdd={() => setAdding(true)} />
      ) : (
        <ul className="space-y-3">
          {remotes.map((remote) => (
            <li key={remote.id}>
              <AddedRemoteCard remote={remote} kinds={kinds} />
            </li>
          ))}
        </ul>
      )}

      {adding ? (
        <AddRemoteForm
          kinds={kinds}
          existingIds={new Set(remotes.map((row) => row.id))}
          onCancel={() => setAdding(false)}
          onAdded={() => {
            setAdding(false)
            void queryClient.invalidateQueries({ queryKey: REMOTES_QUERY_KEY })
          }}
        />
      ) : remotes.length > 0 ? (
        <Button type="button" variant="outline" size="sm" onClick={() => setAdding(true)}>
          <Plus className="mr-1 h-4 w-4" aria-hidden="true" />
          Add remote
        </Button>
      ) : null}
    </section>
  )
}

function EmptyRemotes({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="space-y-3 rounded-box border border-dashed border-base-300 bg-base-200/40 p-4">
      <p className="text-sm text-base-content/70">
        No remotes added. Unused kinds do not appear as cards.
      </p>
      <Button type="button" variant="primary" size="sm" onClick={onAdd}>
        <Plus className="mr-1 h-4 w-4" aria-hidden="true" />
        Add remote
      </Button>
    </div>
  )
}

function AddRemoteForm({
  kinds,
  existingIds,
  onCancel,
  onAdded,
}: {
  kinds: RemoteKind[]
  existingIds: Set<string>
  onCancel: () => void
  onAdded: () => void
}) {
  const available = kinds.filter((kind) => !existingIds.has(kind.id))
  const defaultKind = available.find((kind) => kind.id === 'hermes') ?? available[0]
  const [kindId, setKindId] = useState(defaultKind?.id ?? 'hermes')
  const selected = available.find((kind) => kind.id === kindId) ?? defaultKind
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKeyEnv, setApiKeyEnv] = useState(selected?.api_key_env_default ?? 'HERMES_API_KEY')

  const mutation = useMutation({
    mutationFn: () =>
      addRemote({
        kind: kindId,
        base_url: baseUrl.trim(),
        api_key_env: apiKeyEnv.trim(),
      }),
    onSuccess: onAdded,
  })

  const handleKindChange = (next: string) => {
    const kind = available.find((item) => item.id === next)
    setKindId(next)
    if (kind?.api_key_env_default) {
      setApiKeyEnv(kind.api_key_env_default)
    }
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    mutation.mutate()
  }

  if (available.length === 0) {
    return (
      <Alert type="info" icon={<Server className="h-5 w-5" />}>
        <span className="text-sm">Every known kind is already added.</span>
      </Alert>
    )
  }

  return (
    <form className="space-y-3 rounded-box border border-base-300 p-4" onSubmit={handleSubmit}>
      <h5 className="font-medium">Add remote</h5>
      <Select
        label="Kind"
        name="remote-kind"
        value={kindId}
        onChange={(event) => handleKindChange(event.target.value)}
      >
        {available.map((kind) => (
          <option key={kind.id} value={kind.id}>
            {kind.label}
            {kind.complete ? ' (complete)' : ''}
          </option>
        ))}
      </Select>
      <Input
        label="Base URL"
        name="remote-base-url"
        value={baseUrl}
        onChange={(event) => setBaseUrl(event.target.value)}
        placeholder="http://127.0.0.1:8642"
        autoComplete="off"
        spellCheck={false}
        required
      />
      <Input
        label="API key env name"
        name="remote-api-key-env"
        value={apiKeyEnv}
        onChange={(event) => setApiKeyEnv(event.target.value)}
        placeholder={selected?.api_key_env_default || 'HERMES_API_KEY'}
        autoComplete="off"
        spellCheck={false}
      />
      <p className="text-xs text-base-content/60">
        Store the environment variable name only. Never paste a token.
      </p>
      {mutation.isError ? (
        <Alert type="error" icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">{mutation.error.message}</span>
        </Alert>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="primary" size="sm" loading={mutation.isPending}>
          Add
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  )
}

function AddedRemoteCard({
  remote,
  kinds,
}: {
  remote: RemoteConnection
  kinds: RemoteKind[]
}) {
  const kind = kinds.find((item) => item.id === remote.kind || item.id === remote.id)
  const [prompt, setPrompt] = useState('')
  const [health, setHealth] = useState<RemoteHealthResult | null>(null)
  const [operate, setOperate] = useState<RemoteOperateResult | null>(null)

  const healthMutation = useMutation({
    mutationFn: () => probeRemoteHealth(remote.id),
    onSuccess: (result) => {
      setHealth(result)
      setOperate(null)
    },
  })
  const listMutation = useMutation({
    mutationFn: () => operateRemote(remote.id, 'list'),
    onSuccess: (result) => {
      setOperate(result)
    },
  })
  const sendMutation = useMutation({
    mutationFn: () => operateRemote(remote.id, 'send', prompt),
    onSuccess: (result) => {
      setOperate(result)
    },
  })

  const busy = healthMutation.isPending || listMutation.isPending || sendMutation.isPending
  const report = operate ?? null
  const title = kind?.label || remote.title || remote.id

  const healthTone = useMemo(() => {
    if (!health) return ''
    if (health.state === 'UP') return 'badge-success'
    if (health.state === 'DOWN') return 'badge-error'
    return 'badge-warning'
  }, [health])

  return (
    <article className="space-y-3 rounded-box border border-base-300 bg-base-200/40 p-4">
      <header className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <h5 className="text-base font-semibold">{title}</h5>
          <span className="badge badge-ghost badge-sm font-mono">{remote.kind || remote.id}</span>
          {health ? (
            <span className={`badge badge-sm ${healthTone}`}>{health.state}</span>
          ) : null}
        </div>
        <p className="font-mono text-sm break-all">{remote.base_url}</p>
        <p className="text-xs text-base-content/60">
          API key env: <code>{remote.api_key_env || 'unset'}</code>
        </p>
      </header>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          loading={healthMutation.isPending}
          disabled={busy}
          onClick={() => healthMutation.mutate()}
        >
          Health
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          loading={listMutation.isPending}
          disabled={busy}
          onClick={() => listMutation.mutate()}
        >
          List
        </Button>
      </div>

      {health ? (
        <Alert
          type={health.ok ? 'success' : health.state === 'DOWN' ? 'error' : 'warning'}
          icon={<Server className="h-5 w-5" />}
        >
          <span className="text-sm">
            {health.state}: {health.detail}
          </span>
        </Alert>
      ) : null}

      <div className="space-y-2">
        <Textarea
          label="Send prompt"
          name={`${remote.id}-send-prompt`}
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="status"
          rows={2}
        />
        <Button
          type="button"
          variant="primary"
          size="sm"
          loading={sendMutation.isPending}
          disabled={busy || !prompt.trim()}
          onClick={() => sendMutation.mutate()}
        >
          Send
        </Button>
      </div>

      {report ? (
        <div className="space-y-1">
          <p className="text-sm">
            {report.ok ? 'OK' : 'Failed'}: {report.detail}
          </p>
          {report.data != null ? (
            <pre className="max-h-48 overflow-auto rounded-lg bg-base-300/60 p-2 text-xs">
              {formatJson(report.data)}
            </pre>
          ) : null}
        </div>
      ) : null}

      {(healthMutation.isError || listMutation.isError || sendMutation.isError) && (
        <Alert type="error" icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">
            {(healthMutation.error || listMutation.error || sendMutation.error)?.message}
          </span>
        </Alert>
      )}
    </article>
  )
}

function formatJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}
