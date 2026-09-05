import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  appendTranscript,
  resolveSttPath,
  resolveTtsPath,
  listenSystemStt,
  speakSystem,
  sttUnavailableMessage,
  transcribeCustomBlob,
} from '../speechRuntime'
import { parseSpeechSettings } from '../speechSettings'

function settings(partial: { stt?: object; tts?: object }) {
  return parseSpeechSettings(partial)
}

describe('speechRuntime (REQ-77)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('prefers system STT, falls back to custom only when system is missing', () => {
    const custom = settings({
      stt: { source: 'system', base_url: 'http://127.0.0.1:9' },
      tts: { source: 'system', base_url: '' },
    })
    expect(resolveSttPath(custom, window)).toBeNull()
    expect(sttUnavailableMessage(custom)).toMatch(/not available/i)

    class FakeRec {
      start() {}
      onresult = null
    }
    vi.stubGlobal('SpeechRecognition', FakeRec)
    expect(resolveSttPath(custom, window)).toBe('system')

    const opted = settings({
      stt: { source: 'custom', base_url: 'http://127.0.0.1:9' },
    })
    expect(resolveSttPath(opted, window)).toBe('custom')

    const emptyCustom = settings({ stt: { source: 'custom', base_url: '' } })
    expect(resolveSttPath(emptyCustom, window)).toBeNull()
    expect(sttUnavailableMessage(emptyCustom)).toMatch(/not configured/i)
  })

  it('system STT stub inserts transcript and does not invent a host', async () => {
    class FakeRec {
      onresult: ((event: { results: Array<Array<{ transcript: string }>> }) => void) | null = null
      onend: (() => void) | null = null
      start() {
        queueMicrotask(() => {
          this.onresult?.({ results: [[{ transcript: 'hello from system' }]] })
          this.onend?.()
        })
      }
      stop() {
        this.onend?.()
      }
    }
    vi.stubGlobal('SpeechRecognition', FakeRec)
    const spoken = await new Promise<string>((resolve) => {
      listenSystemStt({
        onTranscript: resolve,
      })
    })
    expect(spoken).toBe('hello from system')
    expect(appendTranscript('draft', spoken)).toBe('draft hello from system')
  })

  it('custom STT posts the stub blob and never sends a live key', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ object: 'transcription', text: 'hello from custom', path: 'custom' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const text = await transcribeCustomBlob(new Blob(['abc'], { type: 'audio/webm' }))
    expect(text).toBe('hello from custom')
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('/v1/speech/transcribe/')
    expect(init?.body).toBeInstanceOf(FormData)
    const body = init.body as FormData
    expect(body.get('file')).toBeInstanceOf(Blob)
    expect(JSON.stringify(init)).not.toMatch(/sk-/)
  })

  it('system TTS uses speechSynthesis and does not call a host', () => {
    const speak = vi.fn()
    const cancel = vi.fn()
    vi.stubGlobal('speechSynthesis', { speak, cancel })
    vi.stubGlobal(
      'SpeechSynthesisUtterance',
      class {
        text: string
        constructor(text: string) {
          this.text = text
        }
      },
    )
    const handle = speakSystem('Read this aloud')
    expect(handle.path).toBe('system')
    expect(speak).toHaveBeenCalledOnce()
    handle.stop()
    expect(cancel).toHaveBeenCalled()
    expect(resolveTtsPath(settings({ tts: { source: 'system', base_url: '' } }), window)).toBe(
      'system',
    )
  })
})
