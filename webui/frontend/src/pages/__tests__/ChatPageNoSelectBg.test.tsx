import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ToastProvider } from '../../components/DaisyUI'
import ChatPage from '../ChatPage'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  url: string
  readyState = 0
  onopen: ((e?: unknown) => void) | null = null
  onclose: ((e?: unknown) => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  send = vi.fn()
  close = vi.fn()

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  open() {
    this.readyState = 1
    this.onopen?.()
  }
}

describe('REQ-204: Chat pane no focus outline / chrome on empty background', () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn()
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ results: [] }),
      } as Response),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders transcript container with select-none, outline-none, focus:outline-none and without focus:outline-primary', async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <MemoryRouter initialEntries={['/chat']}>
            <ChatPage />
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>,
    )

    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const transcript = screen.getByRole('log', { name: 'Conversation' })
    expect(transcript).toBeInTheDocument()
    expect(transcript).toHaveClass('os-chat-transcript')
    expect(transcript).toHaveClass('select-none')
    expect(transcript).toHaveClass('outline-none')
    expect(transcript).toHaveClass('focus:outline-none')
    expect(transcript).not.toHaveClass('focus:outline-primary')
    expect(transcript).not.toHaveClass('focus:outline-2')
  })

  it('renders chat message bubbles with select-text class for copyable text', async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <MemoryRouter initialEntries={['/chat']}>
            <ChatPage />
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>,
    )

    const ws = MockWebSocket.instances[0]
    await act(async () => {
      ws?.open()
    })

    await act(async () => {
      ws?.onmessage?.(
        new MessageEvent('message', {
          data: '<div id="message-list" hx-swap-oob="beforeend"><div class="user-message">Hello from user</div></div>',
        }),
      )
      ws?.onmessage?.(
        new MessageEvent('message', {
          data: '<div id="message-list" hx-swap-oob="beforeend"><div id="message-response-abc123" class="assistant-message"></div></div>',
        }),
      )
      ws?.onmessage?.(
        new MessageEvent('message', {
          data: '<div id="message-response-abc123" class="assistant-message" hx-swap-oob="true">Hello from assistant</div>',
        }),
      )
    })

    const transcript = screen.getByRole('log', { name: 'Conversation' })
    const bubbles = transcript.querySelectorAll('.chat-bubble')
    expect(bubbles.length).toBeGreaterThan(0)
    for (const bubble of bubbles) {
      expect(bubble).toHaveClass('select-text')
    }
  })
})
