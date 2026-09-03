import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RuntimeBanner from '../RuntimeBanner'
import { RUNTIME_BANNER_STORAGE_KEY, clearDismissedRuntimeMode } from '../../lib/runtimeMode'

function renderBanner() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <RuntimeBanner />
    </QueryClientProvider>,
  )
}

function stubRuntime(body: Record<string, unknown>) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => body,
    } as Response),
  )
}

describe('RuntimeBanner', () => {
  beforeEach(() => {
    clearDismissedRuntimeMode()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    clearDismissedRuntimeMode()
  })

  it('warns for bare-metal', async () => {
    stubRuntime({
      mode: 'bare-metal',
      known: true,
      tone: 'warning',
      title: 'This instance is bare metal',
      message: 'This instance is a dedicated harness machine (no container).',
    })
    renderBanner()
    expect(await screen.findByText('This instance is bare metal')).toBeInTheDocument()
    expect(document.querySelector('[data-runtime-tone="warning"]')).toBeTruthy()
    expect(document.querySelector('[data-runtime-tone="info"]')).toBeFalsy()
  })

  it('warns for sandbox-home and uses $HOME placeholder', async () => {
    stubRuntime({
      mode: 'sandbox-home',
      known: true,
      tone: 'warning',
      title: 'Developer sandbox with home access',
      message: 'This instance is a developer sandbox with full access to $HOME (or SWARM_SANDBOX_ROOT).',
    })
    renderBanner()
    expect(await screen.findByText(/developer sandbox with home access/i)).toBeInTheDocument()
    expect(screen.getByText(/\$HOME/)).toBeInTheDocument()
    expect(screen.getByText(/SWARM_SANDBOX_ROOT/)).toBeInTheDocument()
    expect(document.querySelector('[data-runtime-mode="sandbox-home"]')).toBeTruthy()
  })

  it('shows green/info for sandbox-isolated', async () => {
    stubRuntime({
      mode: 'sandbox-isolated',
      known: true,
      tone: 'info',
      title: 'You appear to be in a sandbox env',
      message: 'This instance is compose without $HOME / SWARM_SANDBOX_ROOT mapped.',
    })
    renderBanner()
    expect(await screen.findByText(/you appear to be in a sandbox env/i)).toBeInTheDocument()
    const root = document.querySelector('[data-runtime-tone="info"]')
    expect(root).toBeTruthy()
    expect(root?.querySelector('.alert-success')).toBeTruthy()
  })

  it('shows honest unknown when the env is missing — never fake green', async () => {
    stubRuntime({
      mode: 'unknown',
      known: false,
      tone: 'unknown',
      title: 'Runtime mode unknown',
      message: 'SWARM_RUNTIME_MODE is unset or unrecognized.',
    })
    renderBanner()
    expect(await screen.findByText('Runtime mode unknown')).toBeInTheDocument()
    expect(document.querySelector('[data-runtime-tone="unknown"]')).toBeTruthy()
    expect(document.querySelector('.alert-success')).toBeFalsy()
  })

  it('persists dismiss in localStorage and hides the banner', async () => {
    stubRuntime({
      mode: 'bare-metal',
      known: true,
      tone: 'warning',
      title: 'This instance is bare metal',
      message: 'Dedicated harness.',
    })
    renderBanner()
    expect(await screen.findByText('This instance is bare metal')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss runtime banner' }))
    await waitFor(() => {
      expect(screen.queryByText('This instance is bare metal')).not.toBeInTheDocument()
    })
    expect(localStorage.getItem(RUNTIME_BANNER_STORAGE_KEY)).toBe('bare-metal')
  })
})
