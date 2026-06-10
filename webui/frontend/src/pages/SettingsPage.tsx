import { useState, type FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Eye, EyeOff, KeyRound } from 'lucide-react'
import { Button, Card, Input, useToast } from '../components/DaisyUI'
import { useAuth } from '../lib/AuthContext'

const SettingsPage = () => {
  const { token, setToken, clearAuthError } = useAuth()
  const [draft, setDraft] = useState('')
  const [showDraft, setShowDraft] = useState(false)
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
        {/* API authentication */}
        <Card bordered>
          <h2 className="card-title flex items-center gap-2">
            <KeyRound className="h-5 w-5" />
            API Authentication
          </h2>
          <p className="text-sm text-gray-500">
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

        {/* Application settings */}
        <Card bordered>
          <h2 className="card-title">Application Settings</h2>
          <div className="form-control w-full max-w-xs">
            <label className="label">
              <span className="label-text">Theme</span>
            </label>
            <select className="select select-bordered">
              <option>Light</option>
              <option>Dark</option>
              <option>System</option>
            </select>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default SettingsPage
