import { useMemo, useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Plus, Server } from 'lucide-react'
import { Alert, Button, Input, Select, Textarea, useToast } from './DaisyUI'
import {
  addRemote,
  botsFromOperate,
  fetchRemotes,
  kindById,
  looksLikeSecret,
  operateRemote,
  probeRemoteHealth,
  remoteLabel,
  type RemoteConnection,
  type RemoteHealth,
  type RemoteKind,
  type RemoteOperate,
} from '../lib/remotes'

export const REMOTES_QUERY_KEY = ['settings-remotes'] as const

export function isRemoteSection(section: string): boolean {
  return section === 'remotes' || section.startsWith('remotes-')
}

export function remoteIdFromSection(section: string): string | null {
  if (!section.startsWith('remotes-')) return null
  return section.slice('remotes-'.length) || null
}

export function useRemotesCatalog(enabled: boolean) {
  return useQuery({
    queryKey: REMOTES_QUERY_KEY,
    queryFn: fetchRemotes,
    enabled,
    retry: false,
  })
}

export function RemotesNavItems({
  remotes,
  section,
  onSelect,
}: {
  remotes: RemoteConnection[]
  section: string
  onSelect: (section: string) => void
}) {
  return (
    <>
      <li>
        <button
          type="button"
          className={section === 'remotes' ? 'menu-active' : undefined}
          aria-current={section === 'remotes' ? 'page' : undefined}
          onClick={() => onSelect('remotes')}
        >
          <Plus className="h-3.5 w-3.5" aria-hidden="true" />
          Add remote
        </button>
      </li>
      {remotes.map((remote) => {
        const id = `remotes-${remote.id}`
        return (
          <li key={remote.id}>
            <button
              type="button"
              className={section === id ? 'menu-active' : undefined}
              aria-current={section === id ? 'page' : undefined}
              onClick={() => onSelect(id)}
            >
              {remoteLabel(remote)}
            </button>
          </li>
        )
      })}
    </>
  )
}

export function RemotesPane({
  section,
  remotes,
  kinds,
  onAdded,
}: {
  section: string
  remotes: RemoteConnection[]
  kinds: RemoteKind[]
  onAdded: (remote: RemoteConnection) => void
}) {
  const remoteId = remoteIdFromSection(section)
  const selected = remotes.find((item) => item.id === remoteId)
  if (selected) {
    return <ConfiguredRemotePane remote={selected} kinds={kinds} />
  }
  return <AddRemotePane kinds={kinds} remotes={remotes} onAdded={onAdded} />
}

function AddRemotePane({
  kinds,
  remotes,
  onAdded,
}: {
  kinds: RemoteKind[]
  remotes: RemoteConnection[]
  onAdded: (remote: RemoteConnection) => void
}) {
  const { success, error } = useToast()
  const queryClient = useQueryClient()
  const catalog = kinds.length
    ? kinds
    : [
        {
          id: 'rakazo',
          label: 'Rakazo',
          fields: ['base_url', 'ui_url', 'api_key_env', 'session_cookie_env'],
          ops: ['health', 'list', 'send'],
        },
      ]
  const rakazo = catalog.find((item) => item.id === 'rakazo')
  const [kind, setKind] = useState(rakazo?.id || catalog[0]?.id || 'rakazo')
  const [baseUrl, setBaseUrl] = useState('')
  const [uiUrl, setUiUrl] = useState('')
  const [apiKeyEnv, setApiKeyEnv] = useState('')
  const [sessionCookieEnv, setSessionCookieEnv] = useState('')
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')

  const selectedKind = kindById(catalog, kind)
  const fields = selectedKind?.fields || ['base_url', 'api_key_env']
  const showUi = fields.includes('ui_url')
  const showCookieEnv = fields.includes('session_cookie_env')

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setFormError('')
    if (looksLikeSecret(apiKeyEnv) || looksLikeSecret(sessionCookieEnv)) {
      setFormError('Auth fields are env-var names only. Do not paste a token or cookie.')
      return
    }
    if (!baseUrl.trim()) {
      setFormError('API base URL is required.')
      return
    }
    setBusy(true)
    try {
      const created = await addRemote({
        kind,
        base_url: baseUrl.trim(),
        ui_url: showUi ? uiUrl.trim() : undefined,
        api_key_env: apiKeyEnv.trim() || undefined,
        session_cookie_env: showCookieEnv ? sessionCookieEnv.trim() || undefined : undefined,
      })
      success('Remote added', `${remoteLabel(created)} is ready to health, list, and send.`)
      await queryClient.invalidateQueries({ queryKey: REMOTES_QUERY_KEY })
      onAdded(created)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not add remote'
      setFormError(message)
      error('Add remote failed', message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div>
        <h4 className="text-lg font-semibold">Add remote</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Remotes stay empty until you add one. Pick a kind, then enter the API
          base URL and env-var names for auth — never paste a cookie or token.
        </p>
      </div>
      {remotes.length === 0 && (
        <Alert type="info" icon={<Server className="h-5 w-5" />}>
          <span className="text-sm">No remotes configured yet.</span>
        </Alert>
      )}
      <Select
        label="Kind"
        name="remote-kind"
        value={kind}
        onChange={(event) => setKind(event.target.value)}
      >
        {catalog.map((item) => (
          <option key={item.id} value={item.id}>
            {item.label}
          </option>
        ))}
      </Select>
      <Input
        label="API base URL"
        name="remote-base-url"
        value={baseUrl}
        onChange={(event) => setBaseUrl(event.target.value)}
        placeholder="http://127.0.0.1:3100"
        autoComplete="off"
        spellCheck={false}
      />
      {showUi && (
        <Input
          label="UI URL (optional)"
          name="remote-ui-url"
          value={uiUrl}
          onChange={(event) => setUiUrl(event.target.value)}
          placeholder="http://127.0.0.1:5173"
          autoComplete="off"
          spellCheck={false}
        />
      )}
      <Input
        label="API key env"
        name="remote-api-key-env"
        value={apiKeyEnv}
        onChange={(event) => setApiKeyEnv(event.target.value)}
        placeholder={kind === 'rakazo' ? 'RAKAZO_API_KEY' : 'API_KEY'}
        autoComplete="off"
        spellCheck={false}
      />
      {showCookieEnv && (
        <Input
          label="Session cookie env"
          name="remote-session-cookie-env"
          value={sessionCookieEnv}
          onChange={(event) => setSessionCookieEnv(event.target.value)}
          placeholder="RAKAZO_SESSION_COOKIE"
          autoComplete="off"
          spellCheck={false}
        />
      )}
      {formError && (
        <Alert type="warning" icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">{formError}</span>
        </Alert>
      )}
      <Button type="submit" variant="primary" size="sm" disabled={busy}>
        {busy ? 'Adding…' : 'Save remote'}
      </Button>
    </form>
  )
}

function ConfiguredRemotePane({
  remote,
  kinds,
}: {
  remote: RemoteConnection
  kinds: RemoteKind[]
}) {
  const { error } = useToast()
  const [health, setHealth] = useState<RemoteHealth | null>(null)
  const [listed, setListed] = useState<RemoteOperate | null>(null)
  const [sent, setSent] = useState<RemoteOperate | null>(null)
  const [target, setTarget] = useState('')
  const [prompt, setPrompt] = useState('')
  const [busy, setBusy] = useState<'health' | 'list' | 'send' | null>(null)

  const kind = kindById(kinds, remote.kind || remote.id)
  const bots = useMemo(() => botsFromOperate(listed?.data), [listed])
  const label = remoteLabel(remote)

  const runHealth = async () => {
    setBusy('health')
    try {
      setHealth(await probeRemoteHealth(remote.id))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Health failed'
      setHealth({
        remote: remote.id,
        ok: false,
        state: 'UNKNOWN',
        detail: message,
      })
      error('Health failed', message)
    } finally {
      setBusy(null)
    }
  }

  const runList = async () => {
    setBusy('list')
    try {
      const result = await operateRemote(remote.id, 'list')
      setListed(result)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'List failed'
      setListed({
        remote: remote.id,
        op: 'list',
        ok: false,
        detail: message,
        gap: '',
      })
      error('List failed', message)
    } finally {
      setBusy(null)
    }
  }

  const runSend = async (event: FormEvent) => {
    event.preventDefault()
    setBusy('send')
    try {
      const result = await operateRemote(remote.id, 'send', {
        prompt,
        target,
      })
      setSent(result)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Send failed'
      setSent({
        remote: remote.id,
        op: 'send',
        ok: false,
        detail: message,
        gap: '',
      })
      error('Send failed', message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-lg font-semibold">{label}</h4>
        <p className="mt-1 text-sm text-base-content/70">
          {kind?.notes || remote.notes || 'Health, list, and send through this remote’s API.'}
        </p>
      </div>
      <dl className="space-y-1 text-sm">
        <div>
          <dt className="text-base-content/60">API base URL</dt>
          <dd className="font-mono">{remote.base_url || '—'}</dd>
        </div>
        {remote.ui_url ? (
          <div>
            <dt className="text-base-content/60">UI URL</dt>
            <dd className="font-mono">{remote.ui_url}</dd>
          </div>
        ) : null}
        <div>
          <dt className="text-base-content/60">API key env</dt>
          <dd className="font-mono">{remote.api_key_env || '—'}</dd>
        </div>
        {remote.session_cookie_env || (remote.kind || remote.id) === 'rakazo' ? (
          <div>
            <dt className="text-base-content/60">Session cookie env</dt>
            <dd className="font-mono">{remote.session_cookie_env || '—'}</dd>
          </div>
        ) : null}
        <div>
          <dt className="text-base-content/60">Auth resolved</dt>
          <dd>
            {remote.api_key_set || remote.cookie_set ? 'redacted (env present)' : 'not set in this process'}
          </dd>
        </div>
      </dl>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="primary"
          size="sm"
          disabled={busy !== null}
          onClick={runHealth}
        >
          {busy === 'health' ? 'Checking…' : 'Check health'}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={busy !== null}
          onClick={runList}
        >
          {busy === 'list' ? 'Listing…' : 'List bots'}
        </Button>
      </div>

      {health && (
        <Alert
          type={health.ok ? 'success' : 'warning'}
          icon={<AlertCircle className="h-5 w-5" />}
        >
          <div className="text-sm">
            <p className="font-medium">Health {health.state}</p>
            <p>{health.detail}</p>
          </div>
        </Alert>
      )}

      {listed && (
        <Alert
          type={listed.ok ? 'success' : listed.gap ? 'info' : 'warning'}
          icon={<AlertCircle className="h-5 w-5" />}
        >
          <div className="space-y-1 text-sm">
            <p className="font-medium">{listed.ok ? 'Bots' : 'List'}</p>
            <p>{listed.detail}</p>
            {listed.gap ? <p className="font-mono text-xs">{listed.gap}</p> : null}
            {bots.length > 0 && (
              <ul className="mt-1 list-disc pl-4">
                {bots.map((bot) => (
                  <li key={bot.id}>
                    <button
                      type="button"
                      className="link font-mono"
                      onClick={() => setTarget(bot.id)}
                    >
                      {bot.name ? `${bot.name} (${bot.id})` : bot.id}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Alert>
      )}

      <form className="space-y-3" onSubmit={runSend}>
        <h5 className="font-medium">Send</h5>
        <Input
          label="Bot id"
          name="remote-send-target"
          value={target}
          onChange={(event) => setTarget(event.target.value)}
          placeholder="bot id"
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
        />
        <Button type="submit" variant="primary" size="sm" disabled={busy !== null}>
          {busy === 'send' ? 'Sending…' : 'Send'}
        </Button>
      </form>

      {sent && (
        <Alert
          type={sent.ok ? 'success' : sent.gap ? 'info' : 'warning'}
          icon={<AlertCircle className="h-5 w-5" />}
        >
          <div className="text-sm">
            <p className="font-medium">{sent.ok ? 'Sent' : 'Send'}</p>
            <p>{sent.detail}</p>
            {sent.gap ? <p className="font-mono text-xs">{sent.gap}</p> : null}
          </div>
        </Alert>
      )}
    </div>
  )
}
