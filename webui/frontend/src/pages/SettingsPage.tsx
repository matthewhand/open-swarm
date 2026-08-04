import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Eye, EyeOff, KeyRound, Plug, ServerCog, TerminalSquare } from 'lucide-react'
import { Alert, Button, Card, Input, LoadingSpinner, useToast } from '../components/DaisyUI'
import { ApiAccessPanel } from '../components/ApiAccessPanel'
import { useAuth } from '../lib/AuthContext'
import {
  fetchEnvironmentVariables,
  fetchModels,
  fetchServerSettings,
  type ServerSettingsGroup,
} from '../lib/api'

/**
 * Client-side masking for secret-looking values, applied on top of the
 * server-side masking already done by /settings/api/ and
 * /settings/environment/ (which send '***HIDDEN***' / '***SET***' for
 * sensitive entries). Any value whose name matches KEY/TOKEN/SECRET/PASSWORD
 * is reduced to its last 4 characters.
 */
const SECRET_NAME_PATTERN = /KEY|TOKEN|SECRET|PASSWORD/i
const SERVER_MASKS = new Set(['***HIDDEN***', '***SET***', 'Not Set'])

export function formatSettingValue(name: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  const text = typeof value === 'string' ? value : JSON.stringify(value)
  if (SERVER_MASKS.has(text)) return text
  if (SECRET_NAME_PATTERN.test(name)) {
    return `••••${text.slice(-4)}`
  }
  return text
}

const SettingsPage = () => {
  const { token, setToken, clearAuthError } = useAuth()
  const [draft, setDraft] = useState('')
  const [showDraft, setShowDraft] = useState(false)
  const modelsQuery = useQuery({ queryKey: ['models'], queryFn: fetchModels })
  const modelIds = (modelsQuery.data?.data ?? []).map((m) => m.id)
  const apiBaseUrl = `${window.location.origin}/v1`
  const queryClient = useQueryClient()
  const toast = useToast()

  const applyToken = (next: string | null) => {
    setToken(next)
    clearAuthError()
    setDraft('')
    // Re-run queries so they immediately pick up the new credentials.
    void queryClient.invalidateQueries()
  }

  const handleSave = (event: FormEvent) => {
    event.preventDefault()
    const trimmed = draft.trim()
    if (!trimmed) return
    applyToken(trimmed)
    toast.success('API token saved', 'Requests now send this bearer token.')
  }

  const handleClear = () => {
    applyToken(null)
    toast.info('API token cleared', 'Requests are now sent without a token.')
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Settings</h1>

      <div className="space-y-6">
        {/* API access — connect any OpenAI client */}
        <Card bordered>
          <h2 className="card-title flex items-center gap-2">
            <Plug className="h-5 w-5" />
            API Access
          </h2>
          <ApiAccessPanel baseUrl={apiBaseUrl} token={token} models={modelIds} />
        </Card>

        {/* API authentication */}
        <Card bordered>
          <h2 className="card-title flex items-center gap-2">
            <KeyRound className="h-5 w-5" />
            API Authentication
          </h2>
          <p className="text-sm text-base-content/70">
            The backend uses a static bearer token (its{' '}
            <code>API_AUTH_TOKEN</code> setting). The token is stored locally
            in your browser and sent as an <code>Authorization: Bearer</code>{' '}
            header. If the server runs with auth disabled (e.g. debug
            deployments), no token is needed and everything works without
            one.
          </p>

          <div className="text-sm mt-2">
            {token ? (
              <span>
                Status: <span className="font-medium text-success">token stored</span>{' '}
                (ending in{' '}
                <code>…{token.slice(-4)}</code>)
              </span>
            ) : (
              <span>
                Status:{' '}
                <span className="font-medium">no token stored</span> — requests
                are sent unauthenticated.
              </span>
            )}
          </div>

          <form onSubmit={handleSave} className="mt-2 max-w-md space-y-3">
            <div className="flex items-end gap-2">
              <Input
                label="API token"
                type={showDraft ? 'text' : 'password'}
                placeholder="Paste your API token"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                autoComplete="off"
              />
              <Button
                type="button"
                variant="ghost"
                aria-label={showDraft ? 'Hide token' : 'Show token'}
                onClick={() => setShowDraft((v) => !v)}
              >
                {showDraft ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
            </div>
            <div className="flex gap-2">
              <Button
                type="submit"
                variant="primary"
                disabled={draft.trim().length === 0}
              >
                Save token
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={handleClear}
                disabled={!token}
              >
                Clear token
              </Button>
            </div>
          </form>
        </Card>

        {/* Read-only server settings (GET /settings/api/) */}
        <ServerSettingsCard />

        {/* Read-only environment variables (GET /settings/environment/) */}
        <EnvironmentVariablesCard />
      </div>
    </div>
  )
}

function QueryErrorAlert({
  what,
  error,
  onRetry,
}: {
  what: string
  error: unknown
  onRetry: () => void
}) {
  return (
    <Alert type="error" icon={<AlertCircle className="h-5 w-5" />}>
      <div className="flex flex-col gap-2">
        <span className="font-medium">Failed to load {what}</span>
        <span className="text-sm">
          {error instanceof Error ? error.message : 'Unknown error'}
        </span>
        <div>
          <Button variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      </div>
    </Alert>
  )
}

function SettingsGroupTable({ group }: { group: ServerSettingsGroup }) {
  const entries = Object.entries(group.settings)

  return (
    <details className="collapse collapse-arrow bg-base-200">
      <summary className="collapse-title font-medium">
        {group.icon} {group.title}{' '}
        <span className="text-sm font-normal text-base-content/70">
          ({entries.length} {entries.length === 1 ? 'setting' : 'settings'})
        </span>
      </summary>
      <div className="collapse-content overflow-x-auto">
        <p className="text-sm text-base-content/70 mb-2">{group.description}</p>
        {entries.length === 0 ? (
          <p className="text-sm text-base-content/60">No settings reported in this group.</p>
        ) : (
          <table className="table table-sm">
            <thead>
              <tr>
                <th>Setting</th>
                <th>Value</th>
                <th>Env var</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([settingName, entry]) => (
                <tr key={settingName}>
                  <td>
                    <div className="font-mono text-xs">{settingName}</div>
                    <div className="text-xs text-base-content/70">{entry.description}</div>
                  </td>
                  <td className="font-mono text-xs break-all">
                    {formatSettingValue(settingName, entry.value)}
                  </td>
                  <td className="font-mono text-xs">{entry.env_var ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </details>
  )
}

function ServerSettingsCard() {
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ['server-settings'],
    queryFn: fetchServerSettings,
  })

  const groups = Object.entries(data?.settings ?? {})

  return (
    <Card bordered>
      <h2 className="card-title flex items-center gap-2">
        <ServerCog className="h-5 w-5" />
        Server Settings
      </h2>
      <p className="text-sm text-base-content/70">
        Read-only view of the server configuration reported by{' '}
        <code>/settings/api/</code>. Sensitive values are masked by the server;
        anything secret-looking is additionally reduced to its last 4
        characters client-side.
      </p>

      <div className="mt-3">
        {isPending && (
          <div className="flex items-center gap-2 text-sm text-base-content/70" aria-live="polite" aria-busy="true">
            <LoadingSpinner size="sm" /> Loading server settings…
          </div>
        )}
        {isError && (
          <div aria-live="assertive" role="alert">
            <QueryErrorAlert
              what="server settings"
              error={error}
              onRetry={() => refetch()}
            />
          </div>
        )}
        {!isPending && !isError && groups.length === 0 && (
          <p className="text-sm text-base-content/60">
            The server reported no settings groups.
          </p>
        )}
        {!isPending && !isError && groups.length > 0 && (
          <div className="space-y-2">
            {groups.map(([groupKey, group]) => (
              <SettingsGroupTable key={groupKey} group={group} />
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}

function EnvironmentVariablesCard() {
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ['environment-variables'],
    queryFn: fetchEnvironmentVariables,
  })

  const variables = Object.entries(data?.environment_variables ?? {})

  return (
    <Card bordered>
      <h2 className="card-title flex items-center gap-2">
        <TerminalSquare className="h-5 w-5" />
        Environment Variables
      </h2>
      <p className="text-sm text-base-content/70">
        Swarm-related environment variables on the server, from{' '}
        <code>/settings/environment/</code>. The server replaces values of
        key/token/secret/password variables with <code>***SET***</code>; the
        same masking rule is applied again client-side.
      </p>

      <div className="mt-3">
        {isPending && (
          <div className="flex items-center gap-2 text-sm text-base-content/70" aria-live="polite" aria-busy="true">
            <LoadingSpinner size="sm" /> Loading environment variables…
          </div>
        )}
        {isError && (
          <div aria-live="assertive" role="alert">
            <QueryErrorAlert
              what="environment variables"
              error={error}
              onRetry={() => refetch()}
            />
          </div>
        )}
        {!isPending && !isError && variables.length === 0 && (
          <p className="text-sm text-base-content/60">
            No swarm-related environment variables are set on the server.
          </p>
        )}
        {!isPending && !isError && variables.length > 0 && (
          <div className="overflow-x-auto">
            <table className="table table-sm">
              <thead>
                <tr>
                  <th>Variable</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {variables.map(([key, value]) => (
                  <tr key={key}>
                    <td className="font-mono text-xs">{key}</td>
                    <td className="font-mono text-xs break-all">
                      {formatSettingValue(key, value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Card>
  )
}

export default SettingsPage
