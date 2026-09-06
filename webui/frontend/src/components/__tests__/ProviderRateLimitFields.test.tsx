import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ProviderRateLimitFields from '../ProviderRateLimitFields'
import { ToastProvider } from '../DaisyUI'

function renderFields(providerKey = 'cli:stub', autoFocus = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <ProviderRateLimitFields providerKey={providerKey} autoFocus={autoFocus} />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

describe('ProviderRateLimitFields', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders empty caps on a provider and saves without Django copy', async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (String(url).includes('/v1/rate-limits/') && (!init || init.method === 'GET' || !init.method)) {
        return {
          ok: true,
          json: async () => ({
            object: 'provider_rate_limits',
            data: [
              {
                id: 'cli:stub',
                kind: 'cli',
                name: 'stub',
                object: 'provider_rate_limits',
                rules: {
                  messages_per_minute: null,
                  requests_per_minute: null,
                  tokens_per_minute: null,
                  tokens_per_day: null,
                },
              },
            ],
          }),
        }
      }
      return {
        ok: true,
        json: async () => ({
          object: 'provider_rate_limits',
          data: [],
          saved: { messages_per_minute: 1 },
        }),
      }
    })
    vi.stubGlobal('fetch', fetchMock)

    renderFields('cli:stub')
    const fieldset = await screen.findByTestId('rate-limits-cli-stub')
    expect(fieldset).toHaveAttribute('data-provider', 'cli:stub')
    expect(fieldset.textContent).toMatch(/Empty means no limit/)
    expect(fieldset.textContent).not.toMatch(/Django/i)
    const messages = await screen.findByLabelText('Messages per minute')
    fireEvent.change(messages, { target: { value: '1' } })
    expect(messages).toHaveValue(1)
    fireEvent.click(screen.getByRole('button', { name: 'Save rate limits' }))
    await waitFor(() => {
      const patch = fetchMock.mock.calls.find((call) => String(call[1]?.method || '').toUpperCase() === 'PATCH')
      expect(patch).toBeTruthy()
      const body = JSON.parse(String(patch?.[1]?.body || '{}'))
      expect(body.provider).toBe('cli:stub')
      expect(body.rules.messages_per_minute).toBe(1)
    })
  })
})
