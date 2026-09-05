import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import SettingsSheet from '../SettingsSheet'
import { ToastProvider } from '../DaisyUI'

function renderSheet() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <SettingsSheet isOpen={true} onClose={vi.fn()} />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

describe('Settings Speech (REQ-77)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('saves system/custom sources and api_key_env only — empty URL stays off', async () => {
    let patchPayload: Record<string, unknown> | null = null
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input)
        if (url.includes('/v1/speech/') && init?.method === 'PATCH') {
          patchPayload = JSON.parse(String(init.body))
          const stt = (patchPayload?.stt || {}) as Record<string, string>
          return {
            ok: true,
            status: 200,
            json: async () => ({
              object: 'speech',
              stt: {
                source: stt.source || 'system',
                configured: Boolean(stt.base_url),
                base_url: stt.base_url || '',
                model: stt.model || '',
                api_key_env: stt.api_key_env || '',
                status: stt.source === 'custom' && stt.base_url ? 'down' : 'system',
                detail:
                  stt.source === 'custom' && stt.base_url
                    ? 'Custom STT endpoint is DOWN: stub'
                    : 'Using the browser/OS implementation. No custom host is called.',
              },
              tts: {
                source: 'system',
                configured: false,
                base_url: '',
                model: '',
                api_key_env: 'TTS_API_KEY',
                status: 'system',
                detail: 'Using the browser/OS implementation. No custom host is called.',
              },
            }),
          } as Response
        }
        if (url.includes('/v1/speech/')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              object: 'speech',
              stt: {
                source: 'system',
                configured: false,
                base_url: '',
                model: '',
                api_key_env: '',
                status: 'system',
                detail: 'Using the browser/OS implementation. No custom host is called.',
              },
              tts: {
                source: 'system',
                configured: false,
                base_url: '',
                model: '',
                api_key_env: '',
                status: 'system',
                detail: 'Using the browser/OS implementation. No custom host is called.',
              },
            }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ object: 'list', data: [] }),
        } as Response
      }),
    )

    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'Speech' }))

    await waitFor(() => {
      expect(screen.getByTestId('speech-stt-status')).toHaveTextContent(/browser\/OS/i)
    })

    expect(screen.getByLabelText('STT base URL')).toHaveAttribute(
      'placeholder',
      'Leave empty to keep custom off',
    )
    expect(screen.getByLabelText('STT API key env')).toBeInTheDocument()
    expect(screen.queryByLabelText(/^API key$/i)).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('STT source'), { target: { value: 'custom' } })
    fireEvent.change(screen.getByLabelText('STT base URL'), {
      target: { value: 'http://127.0.0.1:9' },
    })
    fireEvent.change(screen.getByLabelText('STT model id'), { target: { value: 'whisper-1' } })
    fireEvent.change(screen.getByLabelText('STT API key env'), {
      target: { value: 'STT_API_KEY' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save speech' }))

    await waitFor(() => {
      expect(patchPayload).not.toBeNull()
    })
    expect(patchPayload).toEqual({
      stt: {
        source: 'custom',
        base_url: 'http://127.0.0.1:9',
        model: 'whisper-1',
        api_key_env: 'STT_API_KEY',
      },
      tts: {
        source: 'system',
        base_url: '',
        model: '',
        api_key_env: '',
      },
    })
    expect(JSON.stringify(patchPayload)).not.toMatch(/sk-/)
    expect(JSON.stringify(patchPayload)).not.toContain(':8001')
  })
})
