import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Mic, Volume2 } from 'lucide-react'
import { Alert, Button, Input, Select, useToast } from './DaisyUI'
import {
  EMPTY_SPEECH,
  fetchSpeechSettings,
  patchSpeechSettings,
  type SpeechSource,
} from '../lib/api'
import {
  SPEECH_QUERY_KEY,
  parseSpeechSettings,
} from '../lib/speechSettings'

/**
 * Settings → Speech (REQ-77). System/browser is the default for STT and TTS.
 * Custom OpenAI-compat endpoints are opt-in. Api-key env name only.
 */
export default function SpeechPane() {
  const { success, error: toastError } = useToast()
  const queryClient = useQueryClient()
  const [sttSource, setSttSource] = useState<SpeechSource>('system')
  const [sttBaseUrl, setSttBaseUrl] = useState('')
  const [sttModel, setSttModel] = useState('')
  const [sttKeyEnv, setSttKeyEnv] = useState('')
  const [ttsSource, setTtsSource] = useState<SpeechSource>('system')
  const [ttsBaseUrl, setTtsBaseUrl] = useState('')
  const [ttsModel, setTtsModel] = useState('')
  const [ttsKeyEnv, setTtsKeyEnv] = useState('')

  const settingsQuery = useQuery({
    queryKey: SPEECH_QUERY_KEY,
    queryFn: () => fetchSpeechSettings(true),
    retry: 1,
  })

  const parsed = parseSpeechSettings(settingsQuery.data ?? EMPTY_SPEECH)

  useEffect(() => {
    if (!settingsQuery.data) return
    const next = parseSpeechSettings(settingsQuery.data)
    setSttSource(next.stt.source)
    setSttBaseUrl(next.stt.base_url)
    setSttModel(next.stt.model)
    setSttKeyEnv(next.stt.api_key_env)
    setTtsSource(next.tts.source)
    setTtsBaseUrl(next.tts.base_url)
    setTtsModel(next.tts.model)
    setTtsKeyEnv(next.tts.api_key_env)
  }, [settingsQuery.data])

  const saveMutation = useMutation({
    mutationFn: () =>
      patchSpeechSettings({
        stt: {
          source: sttSource,
          base_url: sttBaseUrl.trim(),
          model: sttModel.trim(),
          api_key_env: sttKeyEnv.trim(),
        },
        tts: {
          source: ttsSource,
          base_url: ttsBaseUrl.trim(),
          model: ttsModel.trim(),
          api_key_env: ttsKeyEnv.trim(),
        },
      }),
    onSuccess: (saved) => {
      const next = parseSpeechSettings(saved)
      queryClient.setQueryData(SPEECH_QUERY_KEY, saved)
      setSttSource(next.stt.source)
      setSttBaseUrl(next.stt.base_url)
      setSttModel(next.stt.model)
      setSttKeyEnv(next.stt.api_key_env)
      setTtsSource(next.tts.source)
      setTtsBaseUrl(next.tts.base_url)
      setTtsModel(next.tts.model)
      setTtsKeyEnv(next.tts.api_key_env)
      success('Speech saved', 'Stored env names, not live keys. System stays default until you opt in.')
    },
    onError: (err: Error) => {
      toastError('Could not save speech', err.message)
    },
  })

  const handleSave = (event: FormEvent) => {
    event.preventDefault()
    saveMutation.mutate()
  }

  const sttStatusType =
    parsed.stt.status === 'down' ? 'warning' : parsed.stt.status === 'ok' ? 'success' : 'info'
  const ttsStatusType =
    parsed.tts.status === 'down' ? 'warning' : parsed.tts.status === 'ok' ? 'success' : 'info'

  return (
    <form className="space-y-6" onSubmit={handleSave} data-testid="settings-speech-pane">
      <div>
        <h4 className="text-lg font-semibold">Speech</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Microphone speech-to-text and assistant read-aloud. Default is the
          OS/browser implementation. Custom is an opt-in OpenAI-compatible
          endpoint (<span className="font-mono">/v1/audio/transcriptions</span>{' '}
          and <span className="font-mono">/v1/audio/speech</span>). Leave the
          base URL empty to keep custom off — swarm will not guess a host.
          Store the API key env name only, never a live token.
        </p>
      </div>

      {settingsQuery.isPending ? (
        <p className="text-sm text-base-content/60">Loading speech…</p>
      ) : settingsQuery.isError ? (
        <Alert type="info" icon={<AlertCircle className="h-5 w-5" />}>
          <span className="text-sm">
            Could not load speech settings. Chat still uses the browser/OS
            path — no host is guessed.
          </span>
        </Alert>
      ) : null}

      <section className="space-y-3" aria-labelledby="os-speech-stt-heading">
        <h5 id="os-speech-stt-heading" className="text-base font-semibold">
          Speech-to-text
        </h5>
        {!settingsQuery.isPending && !settingsQuery.isError ? (
          <Alert type={sttStatusType} icon={<Mic className="h-5 w-5" />}>
            <span className="text-sm" data-testid="speech-stt-status">
              {parsed.stt.detail}
            </span>
          </Alert>
        ) : null}
        <Select
          label="STT source"
          name="speech-stt-source"
          size="sm"
          value={sttSource}
          onChange={(event) => setSttSource(event.target.value as SpeechSource)}
        >
          <option value="system">System / browser</option>
          <option value="custom">Custom OpenAI-compatible endpoint</option>
        </Select>
        <Input
          label="STT base URL"
          name="speech-stt-base-url"
          value={sttBaseUrl}
          onChange={(event) => setSttBaseUrl(event.target.value)}
          placeholder="Leave empty to keep custom off"
          autoComplete="off"
          spellCheck={false}
        />
        <Input
          label="STT model id"
          name="speech-stt-model"
          value={sttModel}
          onChange={(event) => setSttModel(event.target.value)}
          placeholder="whisper-1"
          autoComplete="off"
          spellCheck={false}
        />
        <Input
          label="STT API key env"
          name="speech-stt-api-key-env"
          value={sttKeyEnv}
          onChange={(event) => setSttKeyEnv(event.target.value)}
          placeholder="STT_API_KEY"
          autoComplete="off"
          spellCheck={false}
        />
      </section>

      <section className="space-y-3" aria-labelledby="os-speech-tts-heading">
        <h5 id="os-speech-tts-heading" className="text-base font-semibold">
          Read-aloud
        </h5>
        {!settingsQuery.isPending && !settingsQuery.isError ? (
          <Alert type={ttsStatusType} icon={<Volume2 className="h-5 w-5" />}>
            <span className="text-sm" data-testid="speech-tts-status">
              {parsed.tts.detail}
            </span>
          </Alert>
        ) : null}
        <Select
          label="TTS source"
          name="speech-tts-source"
          size="sm"
          value={ttsSource}
          onChange={(event) => setTtsSource(event.target.value as SpeechSource)}
        >
          <option value="system">System / browser</option>
          <option value="custom">Custom OpenAI-compatible endpoint</option>
        </Select>
        <Input
          label="TTS base URL"
          name="speech-tts-base-url"
          value={ttsBaseUrl}
          onChange={(event) => setTtsBaseUrl(event.target.value)}
          placeholder="Leave empty to keep custom off"
          autoComplete="off"
          spellCheck={false}
        />
        <Input
          label="TTS model id"
          name="speech-tts-model"
          value={ttsModel}
          onChange={(event) => setTtsModel(event.target.value)}
          placeholder="tts-1"
          autoComplete="off"
          spellCheck={false}
        />
        <Input
          label="TTS API key env"
          name="speech-tts-api-key-env"
          value={ttsKeyEnv}
          onChange={(event) => setTtsKeyEnv(event.target.value)}
          placeholder="TTS_API_KEY"
          autoComplete="off"
          spellCheck={false}
        />
      </section>

      <p className="text-xs text-base-content/55">
        Persist stores <span className="font-mono">${'{ENV}'}</span> names, not keys.
        A stored custom URL is unused while the source is still system.
      </p>
      <Button type="submit" variant="primary" size="sm" disabled={saveMutation.isPending}>
        Save speech
      </Button>
    </form>
  )
}
