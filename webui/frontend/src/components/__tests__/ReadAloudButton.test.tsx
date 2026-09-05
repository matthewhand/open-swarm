import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ReadAloudButton from '../ReadAloudButton'
import { ToastProvider } from '../DaisyUI'

function renderButton(text = 'Hello from the assistant') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <ReadAloudButton text={text} />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

describe('ReadAloudButton (REQ-77)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uses system speechSynthesis by default and documents the path', async () => {
    const speak = vi.fn()
    const cancel = vi.fn()
    vi.stubGlobal('speechSynthesis', { speak, cancel })
    vi.stubGlobal(
      'SpeechSynthesisUtterance',
      class {
        text: string
        constructor(value: string) {
          this.text = value
        }
      },
    )
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          object: 'speech',
          stt: { source: 'system', configured: false, base_url: '', model: '', api_key_env: '' },
          tts: { source: 'system', configured: false, base_url: '', model: '', api_key_env: '' },
        }),
      } as Response),
    )

    renderButton()
    fireEvent.click(await screen.findByRole('button', { name: 'Read aloud' }))
    await waitFor(() => {
      expect(speak).toHaveBeenCalled()
    })
    expect(await screen.findByTestId('tts-path')).toHaveTextContent(/system/i)
    expect(screen.getByRole('button', { name: 'Stop reading' })).toBeInTheDocument()
  })

  it('toasts when system TTS is missing and custom is unset — no host guessed', async () => {
    vi.stubGlobal('speechSynthesis', undefined)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          object: 'speech',
          stt: { source: 'system', configured: false, base_url: '', model: '', api_key_env: '' },
          tts: { source: 'system', configured: false, base_url: '', model: '', api_key_env: '' },
        }),
      } as Response),
    )
    renderButton()
    fireEvent.click(await screen.findByRole('button', { name: 'Read aloud' }))
    expect(await screen.findByText(/not available/i)).toBeInTheDocument()
    expect(screen.queryByTestId('tts-path')).not.toBeInTheDocument()
  })
})
