import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import CliAgentsSettingsPane from '../CliAgentsSettingsPane'
import { ToastProvider } from '../DaisyUI'

function renderPane() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <CliAgentsSettingsPane />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

describe('CliAgentsSettingsPane (REQ-157)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('starts empty and one-click adds a discovered suggestion', async () => {
    const patches: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input)
        const method = init?.method || 'GET'
        if (url.includes('/v1/config/sections/cli_agents') && method === 'PATCH') {
          patches.push(JSON.parse(String(init?.body || '{}')))
          return {
            ok: true,
            status: 200,
            json: async () => ({ object: 'config_section', data: { grok: { cmd: ['grok'] } } }),
          } as Response
        }
        if (url.includes('/v1/config/sections/cli_agents')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ object: 'config_section', data: {} }),
          } as Response
        }
        if (url.includes('/v1/cli-agents')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              clis: ['agy', 'claude', 'codex', 'gemini', 'grok', 'opencode', 'pi'],
              configured: [],
              discovered: ['grok'],
              installed: ['grok'],
              suggestions: { grok: { cmd: ['grok', '-p', '{prompt}'] } },
              native_consensus: {},
              catalog: {},
            }),
          } as Response
        }
        return { ok: true, status: 200, json: async () => ({}) } as Response
      }),
    )

    renderPane()
    expect(await screen.findByText(/No CLI agents configured yet/i)).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Suggested CLI agents' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))
    await waitFor(() => {
      expect(patches).toEqual([{ upsert: { grok: { cmd: ['grok', '-p', '{prompt}'] } } }])
    })
  })

  it('removes a configured CLI without treating PATH discovery as configured', async () => {
    const patches: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input)
        const method = init?.method || 'GET'
        if (url.includes('/v1/config/sections/cli_agents') && method === 'PATCH') {
          patches.push(JSON.parse(String(init?.body || '{}')))
          return {
            ok: true,
            status: 200,
            json: async () => ({ object: 'config_section', data: {} }),
          } as Response
        }
        if (url.includes('/v1/config/sections/cli_agents')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              object: 'config_section',
              data: { grok: { cmd: ['grok', '-p', '{prompt}'] } },
            }),
          } as Response
        }
        if (url.includes('/v1/cli-agents')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              configured: ['grok'],
              discovered: ['grok', 'claude'],
              suggestions: { claude: { cmd: ['claude'] } },
              native_consensus: {},
              catalog: {},
              clis: [],
            }),
          } as Response
        }
        return { ok: true, status: 200, json: async () => ({}) } as Response
      }),
    )

    renderPane()
    expect(await screen.findByRole('list', { name: 'Configured CLI agents' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    await waitFor(() => {
      expect(patches).toEqual([{ delete: ['grok'] }])
    })
    expect(screen.getByRole('list', { name: 'Suggested CLI agents' })).toBeInTheDocument()
  })
})
