import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '../DaisyUI'
import PluginsServersPane from '../PluginsServersPane'
import { MCP_SERVERS_KEY } from '../../lib/mcpServers'

function renderPane() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <PluginsServersPane />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

describe('PluginsServersPane', () => {
  afterEach(() => {
    localStorage.removeItem(MCP_SERVERS_KEY)
    vi.unstubAllGlobals()
  })

  it('adds, edits, discovers, and removes local/remote servers without storing secrets', async () => {
    const servers: Record<string, unknown>[] = []
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = (init?.method || 'GET').toUpperCase()
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      if (url.includes('/v1/mcp-plugins/discover')) {
        if (body.kind === 'remote') {
          return jsonResponse({
            object: 'mcp_plugin_tools',
            name: body.name,
            kind: 'remote',
            tools: [{ name: 'search_docs', description: 'Search remote docs' }],
          })
        }
        return jsonResponse({
          object: 'mcp_plugin_tools',
          name: body.name,
          kind: 'local',
          tools: [{ name: 'fetch', description: 'Fetch a URL' }],
        })
      }
      if (url.includes('/v1/mcp-plugins/') && method === 'DELETE') {
        const name = decodeURIComponent(url.split('/v1/mcp-plugins/')[1].replace(/\/$/, ''))
        const idx = servers.findIndex((row) => row.name === name)
        if (idx >= 0) servers.splice(idx, 1)
        return jsonResponse({ object: 'mcp_plugins', scope: 'global_servers_per_chat_tools', servers })
      }
      if (url.includes('/v1/mcp-plugins/') && method === 'POST') {
        expect(JSON.stringify(body)).not.toMatch(/sk-|api[_-]?key|bearer /i)
        const existing = servers.findIndex((row) => row.name === body.name)
        const row = {
          name: String(body.name || '')
            .trim()
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '-'),
          label: body.name,
          kind: body.kind,
          enabled: body.enabled !== false,
          command: body.command || '',
          args: body.args || [],
          url: body.url || '',
          env: body.env || {},
          headers: body.headers || {},
          provides: body.provides || [],
          note: body.note || '',
          tools: [],
        }
        if (existing >= 0) servers[existing] = row
        else servers.push(row)
        return jsonResponse({ object: 'mcp_plugins', scope: 'global_servers_per_chat_tools', servers })
      }
      return jsonResponse({ object: 'mcp_plugins', scope: 'global_servers_per_chat_tools', servers })
    })
    vi.stubGlobal('fetch', fetchMock)

    renderPane()
    expect(await screen.findByText(/No servers configured yet/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Fetch' }))
    expect(await screen.findByRole('list', { name: 'Configured MCP servers' })).toHaveTextContent('Fetch')
    expect(localStorage.getItem(MCP_SERVERS_KEY) || '').not.toMatch(/sk-|token|password/i)

    fireEvent.click(screen.getByRole('button', { name: 'Discover tools' }))
    expect(await screen.findByText(/Found 1 tool/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Add server' }))
    fireEvent.change(screen.getByRole('combobox', { name: 'Kind' }), { target: { value: 'remote' } })
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: 'proxy' } })
    fireEvent.change(screen.getByRole('textbox', { name: 'URL' }), {
      target: { value: 'https://example.invalid/mcp' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Auth header name (optional)' }), {
      target: { value: 'Authorization' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Auth header env (optional)' }), {
      target: { value: 'MCP_TOKEN' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save server' }))
    expect((await screen.findAllByText('MCP server saved')).length).toBeGreaterThan(0)
    expect(screen.getByRole('list', { name: 'Configured MCP servers' })).toHaveTextContent('proxy')
    expect(JSON.stringify(fetchMock.mock.calls.map((call) => call[1]?.body))).not.toMatch(/sk-live|Bearer /)

    fireEvent.click(screen.getByRole('button', { name: 'Edit proxy' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Note' }), { target: { value: 'Remote mock' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save server' }))
    await waitFor(() => {
      expect(screen.getAllByText('MCP server saved').length).toBeGreaterThan(0)
    })

    const removeButtons = screen.getAllByRole('button', { name: 'Remove' })
    fireEvent.click(removeButtons[0])
    await waitFor(() => {
      expect(screen.getByRole('list', { name: 'Configured MCP servers' })).not.toHaveTextContent('Fetch')
    })
  })

  it('shows an honest toast when discover fails', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = (init?.method || 'GET').toUpperCase()
      if (url.includes('/v1/mcp-plugins/discover')) {
        return jsonResponse({ error: 'mock MCP refused connect', code: 'mcp_discover_failed' }, 502)
      }
      if (method === 'GET') {
        return jsonResponse({
          object: 'mcp_plugins',
          scope: 'global_servers_per_chat_tools',
          servers: [
            {
              name: 'fetch',
              kind: 'local',
              enabled: true,
              command: 'uvx',
              args: ['mcp-server-fetch'],
              url: '',
              env: {},
              headers: {},
              provides: ['fetch'],
              note: '',
              tools: [],
            },
          ],
        })
      }
      return jsonResponse({ object: 'mcp_plugins', scope: 'global_servers_per_chat_tools', servers: [] })
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPane()
    expect(await screen.findByRole('list', { name: 'Configured MCP servers' })).toHaveTextContent(
      'fetch',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Discover tools' }))
    expect(await screen.findByText('Could not list tools')).toBeInTheDocument()
    expect(screen.getByText(/refused connect/i)).toBeInTheDocument()
  })
})
