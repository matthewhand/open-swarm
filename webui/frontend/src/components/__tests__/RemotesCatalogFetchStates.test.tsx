import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import SettingsSheet from '../SettingsSheet'
import { ToastProvider } from '../DaisyUI'

function renderSheet() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const onClose = vi.fn()
  const view = render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <SettingsSheet isOpen={true} onClose={onClose} />
      </ToastProvider>
    </QueryClientProvider>,
  )
  return { ...view, onClose, client }
}

describe('REQ-188A-4: Remotes distinct loading, error, and empty states', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows loading indicator when GET /v1/remotes/ is pending', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/v1/remotes/')) {
          // Never resolving promise to simulate pending fetch
          return new Promise(() => {})
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ object: 'list', data: [] }),
        } as Response)
      }),
    )

    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'Remotes' }))

    expect(screen.getByTestId('remotes-loading')).toHaveTextContent('Loading remotes…')
    expect(screen.queryByText('No remotes configured yet.')).not.toBeInTheDocument()
    expect(screen.queryByTestId('remotes-error')).not.toBeInTheDocument()
  })

  it('shows error banner with retry button when GET /v1/remotes/ fails', async () => {
    let callCount = 0
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/v1/remotes/')) {
          callCount += 1
          if (callCount <= 2) {
            return {
              ok: false,
              status: 500,
              statusText: 'Internal Server Error',
              text: async () => 'Database unreachable',
            } as Response
          }
          return {
            ok: true,
            status: 200,
            json: async () => ({
              object: 'list',
              kinds: [{ id: 'omb', label: 'OpenMousBot' }],
              configured: [],
              data: [],
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
    fireEvent.click(screen.getByRole('button', { name: 'Remotes' }))

    const errorContainer = await screen.findByTestId('remotes-error', undefined, { timeout: 4000 })
    expect(errorContainer).toHaveTextContent('Failed to load remotes catalog.')
    expect(screen.queryByText('No remotes configured yet.')).not.toBeInTheDocument()
    expect(screen.queryByTestId('remotes-loading')).not.toBeInTheDocument()

    // Test retry
    const retryBtn = screen.getByRole('button', { name: 'Retry' })
    fireEvent.click(retryBtn)

    await waitFor(() => {
      expect(screen.getByText('No remotes configured yet.')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('remotes-error')).not.toBeInTheDocument()
  })

  it('shows honest empty state when GET /v1/remotes/ succeeds with zero configured remotes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/v1/remotes/')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              object: 'list',
              kinds: [{ id: 'omb', label: 'OpenMousBot' }],
              configured: [],
              data: [],
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
    fireEvent.click(screen.getByRole('button', { name: 'Remotes' }))

    expect(await screen.findByText('No remotes configured yet.')).toBeInTheDocument()
    expect(screen.queryByTestId('remotes-loading')).not.toBeInTheDocument()
    expect(screen.queryByTestId('remotes-error')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Add remote/i })).toBeInTheDocument()
  })
})
