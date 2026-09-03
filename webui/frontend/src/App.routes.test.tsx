import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App, { chatPathWithSearch } from './App'
import { HIDDEN_AGENTS_STORAGE_KEY } from './lib/hiddenAgents'

class MockWebSocket {
  static OPEN = 1
  static CONNECTING = 0
  static instances: MockWebSocket[] = []

  readyState = MockWebSocket.CONNECTING
  onopen: ((ev?: Event) => void) | null = null
  onmessage: ((ev?: Event) => void) | null = null
  onclose: ((ev?: Event) => void) | null = null
  send = vi.fn()
  close = vi.fn()

  constructor(_url: string) {
    MockWebSocket.instances.push(this)
  }

  open() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.(new Event('open'))
  }
}

function renderAppAt(path: string) {
  window.history.pushState({}, '', path)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  )
}

describe('chatPathWithSearch', () => {
  it('keeps /chat and preserves the query string', () => {
    expect(chatPathWithSearch('')).toBe('/chat')
    expect(chatPathWithSearch('?blueprint=codey')).toBe('/chat?blueprint=codey')
    expect(chatPathWithSearch('blueprint=codey')).toBe('/chat?blueprint=codey')
  })
})

describe('SPA /chat stays Chat (not /agents)', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    Element.prototype.scrollIntoView = vi.fn()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ data: [] }),
      } as Response),
    )
    window.history.pushState({}, '', '/')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders composer + silent healthy status at /chat', async () => {
    renderAppAt('/chat')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })
    expect(window.location.pathname).toBe('/chat')
    expect(screen.getByRole('textbox', { name: 'Chat message' })).toBeInTheDocument()
    expect(screen.getByLabelText('Connection status')).toHaveTextContent('')
    expect(screen.queryByRole('navigation', { name: 'Primary' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /^Chat$/ })).not.toBeInTheDocument()
  })

  it('aliases /agents onto /chat and keeps the composer', async () => {
    renderAppAt('/agents?blueprint=codey')
    await waitFor(() => {
      expect(window.location.pathname).toBe('/chat')
    })
    expect(window.location.search).toBe('?blueprint=codey')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })
    expect(screen.getByRole('textbox', { name: 'Chat message' })).toBeInTheDocument()
    expect(screen.getByLabelText('Connection status')).toHaveTextContent('')
    expect(screen.getByLabelText('Agent name')).toHaveValue('codey')
  })

  it('does not add a /settings SPA page that unmounts Chat', async () => {
    renderAppAt('/settings')
    await waitFor(() => {
      expect(window.location.pathname).toBe('/')
    })
    expect(screen.getByRole('textbox', { name: 'Chat message' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /settings/i })).not.toBeInTheDocument()
  })

  it('does not add a /hidden SPA page; Hidden Bots stays an overlay', async () => {
    renderAppAt('/hidden')
    await waitFor(() => {
      expect(window.location.pathname).toBe('/')
    })
    expect(screen.getByRole('textbox', { name: 'Chat message' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Hidden Bots' })).not.toBeInTheDocument()
  })

  it('keeps the Chat composer mounted while Hidden Bots is an overlay', async () => {
    window.localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(['codey']))
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          object: 'list',
          data: [
            {
              id: 'codey',
              object: 'blueprint',
              name: 'Codey',
              description: 'Code assistant',
              abbreviation: null,
              required_mcp_servers: [],
              tags: [],
              installed: true,
              compiled: true,
            },
          ],
        }),
      } as Response),
    )
    renderAppAt('/chat')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })
    fireEvent.click(await screen.findByRole('button', { name: /^Hidden Bots/ }))
    expect(screen.getByRole('dialog', { name: /Hidden Bots/i })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Chat message' })).toBeInTheDocument()
  })
})
