import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App, { chatPathWithSearch } from './App'

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

  it('renders composer + connection status at /chat', async () => {
    renderAppAt('/chat')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })
    expect(window.location.pathname).toBe('/chat')
    expect(screen.getByRole('textbox', { name: 'Chat message' })).toBeInTheDocument()
    expect(screen.getByLabelText('Connection status')).toHaveTextContent('Connected')
    const chatItems = screen.getAllByRole('menuitem', { name: /Chat/ })
    expect(chatItems.length).toBeGreaterThan(0)
    for (const item of chatItems) {
      expect(item).toHaveAttribute('href', '/chat')
    }
  })

  it('mounts Agent Router at /agents', async () => {
    renderAppAt('/agents')
    expect(window.location.pathname).toBe('/agents')
    expect(await screen.findByRole('complementary', { name: 'Agent sidebar' })).toBeInTheDocument()
  })

  it('keeps Agents in the primary nav and parks the rest under More', () => {
    renderAppAt('/agents')
    const primary = screen.getByRole('navigation', { name: 'Primary' })
    expect(primary.querySelector('a[href="/agents"]')).toBeTruthy()
    const more = screen.getAllByRole('button', { name: 'More' })
    expect(more.length).toBeGreaterThan(0)
    const chatItems = screen.getAllByRole('menuitem', { name: /Chat/ })
    expect(chatItems.length).toBeGreaterThan(0)
    for (const item of chatItems) {
      expect(item).toHaveAttribute('href', '/chat')
    }
    const blueprintItems = screen.getAllByRole('menuitem', { name: /Blueprints/ })
    expect(blueprintItems[0]).toHaveAttribute('href', '/blueprint-library/')
  })
})
