import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Image as ImageIcon } from 'lucide-react'
import { Alert, Button, Input, useToast } from './DaisyUI'
import {
  EMPTY_IMAGE_GEN,
  fetchImageGenSettings,
  patchImageGenSettings,
} from '../lib/api'
import {
  IMAGE_GEN_QUERY_KEY,
  isImageGenConfigured,
  parseImageGenSettings,
} from '../lib/imageGenSettings'

/**
 * Settings → Image generation (REQ-83). Base URL, model id, api-key env name
 * only. Empty/off does not guess a host.
 */
export default function ImageGenPane() {
  const { success, error: toastError } = useToast()
  const queryClient = useQueryClient()
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState('')
  const [apiKeyEnv, setApiKeyEnv] = useState('')

  const settingsQuery = useQuery({
    queryKey: IMAGE_GEN_QUERY_KEY,
    queryFn: () => fetchImageGenSettings(true),
    retry: 1,
  })

  const parsed = parseImageGenSettings(settingsQuery.data ?? EMPTY_IMAGE_GEN)

  useEffect(() => {
    if (!settingsQuery.data) return
    const next = parseImageGenSettings(settingsQuery.data)
    setBaseUrl(next.base_url)
    setModel(next.model)
    setApiKeyEnv(next.api_key_env)
  }, [settingsQuery.data])

  const saveMutation = useMutation({
    mutationFn: () =>
      patchImageGenSettings({
        base_url: baseUrl.trim(),
        model: model.trim(),
        api_key_env: apiKeyEnv.trim(),
      }),
    onSuccess: (saved) => {
      const next = parseImageGenSettings(saved)
      queryClient.setQueryData(IMAGE_GEN_QUERY_KEY, saved)
      setBaseUrl(next.base_url)
      setModel(next.model)
      setApiKeyEnv(next.api_key_env)
      success(
        next.base_url ? 'Image generation saved' : 'Image generation off',
        next.detail || 'Stored the env name, not a live key.',
      )
    },
    onError: (err: Error) => {
      toastError('Could not save image generation', err.message)
    },
  })

  const handleSave = (event: FormEvent) => {
    event.preventDefault()
    saveMutation.mutate()
  }

  const configured = isImageGenConfigured(parsed)
  const status = parsed.status || (configured ? 'unknown' : 'off')
  const statusType =
    status === 'down' ? 'warning' : status === 'ok' ? 'success' : 'info'

  return (
    <form className="space-y-4" onSubmit={handleSave} data-testid="settings-image-gen-pane">
      <div>
        <h4 className="text-lg font-semibold">Image generation</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Opt-in OpenAI-compatible <span className="font-mono">/v1/images/generations</span>{' '}
          endpoint for still agent avatars. Leave the base URL empty to keep this
          off — swarm will not guess a host. Store the API key env name only,
          never a live token. Distinct from Rail → Blobs with eyes.
        </p>
      </div>

      {settingsQuery.isPending ? (
        <p className="text-sm text-base-content/60">Loading image generation…</p>
      ) : settingsQuery.isError ? (
        <Alert type="info" icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">
            Could not load image generation settings. The endpoint is treated as
            off until Settings can read it — no host is guessed.
          </span>
        </Alert>
      ) : (
        <Alert type={statusType} icon={<ImageIcon className="h-5 w-5" />}>
          <span className="text-sm" data-testid="image-gen-status">
            {parsed.detail}
          </span>
        </Alert>
      )}

      <Input
        label="Base URL"
        name="image-gen-base-url"
        value={baseUrl}
        onChange={(event) => setBaseUrl(event.target.value)}
        placeholder="Leave empty to keep off"
        autoComplete="off"
        spellCheck={false}
      />
      <Input
        label="Model id"
        name="image-gen-model"
        value={model}
        onChange={(event) => setModel(event.target.value)}
        placeholder="Model id your endpoint expects"
        autoComplete="off"
        spellCheck={false}
      />
      <Input
        label="API key env (optional)"
        name="image-gen-api-key-env"
        value={apiKeyEnv}
        onChange={(event) => setApiKeyEnv(event.target.value)}
        placeholder="IMAGE_GEN_API_KEY"
        autoComplete="off"
        spellCheck={false}
      />
      <p className="text-xs text-base-content/55">
        Persist stores <span className="font-mono">${'{ENV}'}</span> names, not keys.
        Generate avatar in the agent editor stays disabled until a base URL is
        saved.
      </p>
      <Button type="submit" variant="primary" size="sm" disabled={saveMutation.isPending}>
        Save image generation
      </Button>
    </form>
  )
}
