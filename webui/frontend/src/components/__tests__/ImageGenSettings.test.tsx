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

describe('Settings Image generation (REQ-83)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('saves base URL, model, and api_key_env only — empty URL stays off', async () => {
    let patchPayload: Record<string, unknown> | null = null
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input)
        if (url.includes('/v1/image-gen/') && init?.method === 'PATCH') {
          patchPayload = JSON.parse(String(init.body))
          return {
            ok: true,
            status: 200,
            json: async () => ({
              object: 'image_gen',
              configured: Boolean(patchPayload?.base_url),
              base_url: patchPayload?.base_url || '',
              model: patchPayload?.model || '',
              api_key_env: patchPayload?.api_key_env || '',
              status: patchPayload?.base_url ? 'down' : 'off',
              detail: patchPayload?.base_url
                ? 'Image generation endpoint is DOWN: stub'
                : 'Image generation is off. No host is used until you set a base URL.',
              avatars: {},
            }),
          } as Response
        }
        if (url.includes('/v1/image-gen/')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              object: 'image_gen',
              configured: false,
              base_url: '',
              model: '',
              api_key_env: '',
              status: 'off',
              detail: 'Image generation is off. No host is used until you set a base URL.',
              avatars: {},
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
    fireEvent.click(screen.getByRole('button', { name: 'Image generation' }))

    await waitFor(() => {
      expect(screen.getByTestId('image-gen-status')).toHaveTextContent(/off/i)
    })

    expect(screen.getByLabelText('Base URL')).toHaveAttribute(
      'placeholder',
      'Leave empty to keep off',
    )
    expect(screen.getByLabelText(/API key env/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/^API key$/i)).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Base URL'), {
      target: { value: 'http://127.0.0.1:9' },
    })
    fireEvent.change(screen.getByLabelText('Model id'), { target: { value: 'still-1' } })
    fireEvent.change(screen.getByLabelText(/API key env/i), {
      target: { value: 'IMAGE_GEN_API_KEY' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save image generation' }))

    await waitFor(() => {
      expect(patchPayload).not.toBeNull()
    })
    expect(patchPayload).toEqual({
      base_url: 'http://127.0.0.1:9',
      model: 'still-1',
      api_key_env: 'IMAGE_GEN_API_KEY',
    })
    expect(patchPayload).not.toHaveProperty('api_key')

    fireEvent.change(screen.getByLabelText('Base URL'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save image generation' }))
    await waitFor(() => {
      expect(patchPayload?.base_url).toBe('')
    })
    expect(patchPayload).not.toHaveProperty('api_key')
  })
})
