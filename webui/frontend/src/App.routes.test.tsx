import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
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
  close = vi.fn(() => {
    this.readyState = 3
    this.onclose?.(new CloseEvent('close', { code: 1000 }))
  })

  constructor(_url: string) {
    MockWebSocket.instances.push(this)
  }

  open() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.(new Event('open'))
  }

  drop() {
    this.readyState = 3
    this.onclose?.(new CloseEvent('close', { code: 1006 }))
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
    expect(screen.getByRole('heading', { name: 'codey' })).toBeInTheDocument()
  })
})

describe('REQ-53 hostname rail icon', () => {
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

  it('is bland when connected and red after a mocked socket drop', async () => {
    renderAppAt('/chat')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const connected = await screen.findByTestId('os-rail-hostname-icon')
    expect(connected).toHaveAttribute('data-tone', 'bland')
    expect(connected).not.toHaveClass('text-error')
    expect(connected.className).not.toMatch(/text-error|text-success|text-green/)

    await act(async () => {
      MockWebSocket.instances[0]?.drop()
    })

    const dropped = await screen.findByTestId('os-rail-hostname-icon')
    expect(dropped).toHaveAttribute('data-tone', 'error')
    expect(dropped).toHaveClass('text-error')

    const reconnect = await screen.findByRole('button', { name: /Reconnect/i })
    fireEvent.click(reconnect)
    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(2)
    })
    await act(async () => {
      MockWebSocket.instances[MockWebSocket.instances.length - 1]?.open()
    })

    const restored = await screen.findByTestId('os-rail-hostname-icon')
    expect(restored).toHaveAttribute('data-tone', 'bland')
    expect(restored).not.toHaveClass('text-error')
  })
})
