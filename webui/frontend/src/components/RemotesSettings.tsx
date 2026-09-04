import { useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Plus, Server } from 'lucide-react'
import { Alert, Button, Input, Select, Textarea, useToast } from './DaisyUI'
import {
  addRemote,
  operateRemote,
  probeRemoteHealth,
  type RemoteConnection,
  type RemoteHealthResult,
  type RemoteKind,
  type RemoteOperateResult,
} from '../lib/api'
import { isOpenMousBotKind, OPENMOUSBOT_LABEL, remoteKindLabel } from '../lib/remoteKinds'

export const REMOTES_QUERY_KEY = ['settings-remotes'] as const

export function configuredRemoteSection(id: string): `remotes-${string}` {
  return `remotes-${id}`
}

export function EmptyRemotesPane({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-lg font-semibold">Remotes</h4>
        <p className="mt-1 text-sm text-base-content/70">
          No remotes configured. Add a kind to health-check it, list its bots,
          and send a message. Unused kinds stay out of this list.
        </p>
      </div>
      <Button type="button" variant="primary" size="sm" onClick={onAdd}>
        <Plus className="h-4 w-4" aria-hidden="true" />
        Add remote
      </Button>
    </div>
  )
}

export function AddRemoteForm({
  kinds,
  onAdded,
}: {
  kinds: RemoteKind[]
  onAdded: (remote: RemoteConnection) => void
}) {
  const { success, error } = useToast()
  const queryClient = useQueryClient()
  const options = kinds.length
    ? kinds
    : [
        { id: 'hermes', label: 'Hermes' },
        { id: 'omb', label: OPENMOUSBOT_LABEL },
        { id: 'rakazo', label: 'Rakazo' },
      ]
  const [kind, setKind] = useState(options[0]?.id ?? 'omb')
  const [baseUrl, setBaseUrl] = useState('')
  const [uiUrl, setUiUrl] = useState('')
  const [apiKeyEnv, setApiKeyEnv] = useState('')
  const [sessionCookieEnv, setSessionCookieEnv] = useState('')

  const addMutation = useMutation({
    mutationFn: () =>
      addRemote({
        kind,
        base_url: baseUrl.trim(),
        ui_url: uiUrl.trim() || undefined,
        api_key_env: apiKeyEnv.trim() || undefined,
        session_cookie_env: sessionCookieEnv.trim() || undefined,
      }),
    onSuccess: (remote) => {
      queryClient.setQueryData(REMOTES_QUERY_KEY, (prev: { object?: string; kinds?: RemoteKind[]; data?: RemoteConnection[] } | undefined) => {
        const kinds = prev?.kinds ?? []
        const data = [...(prev?.data ?? []).filter((row) => row.id !== remote.id), remote]
        return { object: 'list' as const, kinds, data }
      })
      queryClient.invalidateQueries({ queryKey: REMOTES_QUERY_KEY })
      success('Remote added', remoteKindLabel(remote.id, remote.label))
      onAdded(remote)
    },
    onError: (err: Error) => {
      error('Could not add remote', err.message)
    },
  })

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    addMutation.mutate()
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div>
        <h4 className="text-lg font-semibold">Add remote</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Pick a kind, then enter a base URL and an optional api-key-env name
          (placeholder only — never paste a token).
        </p>
      </div>
      <Select
        label="Kind"
        name="remote-kind"
        value={kind}
        onChange={(event) => setKind(event.target.value)}
        required
      >
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {remoteKindLabel(option.id, option.label)}
          </option>
        ))}
      </Select>
      <Input
        label="Base URL"
        name="remote-base-url"
        value={baseUrl}
        onChange={(event) => setBaseUrl(event.target.value)}
        placeholder="http://127.0.0.1:9"
        autoComplete="off"
        spellCheck={false}
        required
      />
      {kind === 'rakazo' ? (
        <Input
          label="UI URL"
          name="remote-ui-url"
          value={uiUrl}
          onChange={(event) => setUiUrl(event.target.value)}
          placeholder="http://127.0.0.1:5173"
          autoComplete="off"
          spellCheck={false}
        />
      ) : null}
      <Input
        label="API key env (optional)"
        name="remote-api-key-env"
        value={apiKeyEnv}
        onChange={(event) => setApiKeyEnv(event.target.value)}
        placeholder="OMB_API_KEY"
        autoComplete="off"
        spellCheck={false}
      />
      {kind === 'rakazo' ? (
        <Input
          label="Session cookie env (optional)"
          name="remote-session-cookie-env"
          value={sessionCookieEnv}
          onChange={(event) => setSessionCookieEnv(event.target.value)}
          placeholder="RAKAZO_SESSION_COOKIE"
          autoComplete="off"
          spellCheck={false}
        />
      ) : null}
      <p className="text-xs text-base-content/60">
        Env-var names only — never paste a token or cookie.
      </p>
      <Button type="submit" variant="primary" size="sm" loading={addMutation.isPending}>
        Add remote
      </Button>
    </form>
  )
}

function botsFromOperate(result: RemoteOperateResult | undefined): Array<{ id: string; name?: string }> {
  if (!result?.data) return []
  const raw = result.data
  let list: unknown = raw
  if (raw && typeof raw === 'object') {
    const rec = raw as { bots?: unknown; json?: unknown }
    if (Array.isArray(rec.bots)) list = rec.bots
    else if (Array.isArray(rec.json)) list = rec.json
  }
  if (!Array.isArray(list)) return []
  return list
    .map((item) => {
      if (typeof item === 'string') return { id: item }
      if (item && typeof item === 'object' && 'id' in item) {
        const rec = item as { id: unknown; name?: unknown }
        return { id: String(rec.id), name: rec.name != null ? String(rec.name) : undefined }
      }
      return null
    })
    .filter((item): item is { id: string; name?: string } => Boolean(item?.id))
}

export function RemoteOperatePane({ remote }: { remote: RemoteConnection }) {
  const { error } = useToast()
  const label = remoteKindLabel(remote.id, remote.label || remote.title)
  const isOmb = isOpenMousBotKind(remote.id)
  const isRakazo = remote.id === 'rakazo'
  const listsBots = isOmb || isRakazo
  const [health, setHealth] = useState<RemoteHealthResult | null>(null)
  const [listed, setListed] = useState<RemoteOperateResult | null>(null)
  const [sent, setSent] = useState<RemoteOperateResult | null>(null)
  const [botId, setBotId] = useState('')
  const [prompt, setPrompt] = useState('')

  const healthMutation = useMutation({
    mutationFn: () => probeRemoteHealth(remote.id),
    onSuccess: (result) => setHealth(result),
    onError: (err: Error) => {
      setHealth({
        remote: remote.id,
        ok: false,
        state: 'DOWN',
        detail: err.message || 'health probe failed',
      })
    },
  })

  const listMutation = useMutation({
    mutationFn: () => operateRemote(remote.id, { op: 'list' }),
    onSuccess: (result) => {
      setListed(result)
      const bots = botsFromOperate(result)
      if (!botId && bots[0]?.id) setBotId(bots[0].id)
    },
    onError: (err: Error) => {
      setListed({
        remote: remote.id,
        op: 'list',
        ok: false,
        detail: err.message || 'list failed',
      })
    },
  })

  const sendMutation = useMutation({
    mutationFn: () =>
      operateRemote(remote.id, { op: 'send', prompt: prompt.trim(), target: botId.trim() }),
    onSuccess: (result) => setSent(result),
    onError: (err: Error) => {
      error('Send failed', err.message)
      setSent({
        remote: remote.id,
        op: 'send',
        ok: false,
        detail: err.message || 'send failed',
      })
    },
  })

  const bots = useMemo(() => botsFromOperate(listed ?? undefined), [listed])
  const healthTone =
    health?.state === 'UP' ? 'success' : health?.state === 'DOWN' ? 'warning' : health ? 'info' : undefined

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-lg font-semibold">{label}</h4>
        <p className="mt-1 text-sm text-base-content/70">
          {remote.base_url || 'No base URL'}
          {remote.api_key_env ? ` · env ${remote.api_key_env}` : ''}
          {remote.session_cookie_env ? ` · cookie-env ${remote.session_cookie_env}` : ''}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          loading={healthMutation.isPending}
          onClick={() => healthMutation.mutate()}
        >
          Health
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          loading={listMutation.isPending}
          onClick={() => listMutation.mutate()}
        >
          {listsBots ? 'List bots' : 'List'}
        </Button>
      </div>

      {health && (
        <Alert
          type={healthTone === 'success' ? 'success' : healthTone === 'warning' ? 'warning' : 'info'}
          icon={<Server className="h-5 w-5" />}
        >
          <div className="space-y-1 text-sm">
            <p>
              <span className="font-medium">{health.state}</span>
              {health.ok ? '' : ' — report, not a crash'}
            </p>
            <p className="text-base-content/70">{health.detail}</p>
          </div>
        </Alert>
      )}

      {listed && (
        <div className="space-y-2">
          <p className="text-sm font-medium">{listsBots ? 'Bots' : 'List'}</p>
          {listed.ok && bots.length > 0 ? (
            <ul className="space-y-1 text-sm">
              {bots.map((bot) => (
                <li key={bot.id} className="rounded-lg border border-base-300 bg-base-200/60 px-3 py-2 font-mono">
                  {bot.id}
                  {bot.name ? ` · ${bot.name}` : ''}
                </li>
              ))}
            </ul>
          ) : (
            <Alert type={listed.ok ? 'info' : 'warning'} icon={<AlertCircle className="h-5 w-5" />}>
              <div className="space-y-1 text-sm">
                <span>{listed.detail}</span>
                {listed.gap ? <p className="font-mono text-xs">{listed.gap}</p> : null}
              </div>
            </Alert>
          )}
        </div>
      )}

      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault()
          sendMutation.mutate()
        }}
      >
        <Input
          label={isOmb ? 'Bot id' : 'Target'}
          name="remote-bot-id"
          value={botId}
          onChange={(event) => setBotId(event.target.value)}
          placeholder={isOmb ? 'bot id' : 'optional target'}
          autoComplete="off"
          spellCheck={false}
        />
        <Textarea
          label="Message"
          name="remote-send-prompt"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Message to send"
          rows={3}
          required
        />
        <Button type="submit" variant="primary" size="sm" loading={sendMutation.isPending}>
          Send
        </Button>
      </form>

      {sent && (
        <Alert type={sent.ok ? 'success' : 'warning'} icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">{sent.detail}</span>
        </Alert>
      )}
    </div>
  )
}
