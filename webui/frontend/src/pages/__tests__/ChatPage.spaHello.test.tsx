import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ChatPage from '../ChatPage'
import { ToastProvider } from '../../components/DaisyUI'
import { resetConversationThreads } from '../../lib/chatMeter'
import {
  SPA_HELLO_EVENT,
  getExpectedSpaVersion,
  resetExpectedSpaVersion,
} from '../../lib/spaHello'

class MockWebSocket {
  static OPEN = 1
  static CONNECTING = 0
  static instances: MockWebSocket[] = []

  readyState = MockWebSocket.CONNECTING
  onopen: ((ev?: Event) => void) | null = null
  onmessage: ((ev?: MessageEvent) => void) | null = null
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

describe('ChatPage spa_hello (REQ-78)', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    resetExpectedSpaVersion()
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
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetConversationThreads()
    resetExpectedSpaVersion()
  })

  it('publishes the backend SPA version from a mocked WS hello', async () => {
    const seen: string[] = []
    const onHello = (event: Event) => {
      const detail = (event as CustomEvent<string | null>).detail
      if (detail) seen.push(detail)
    }
    window.addEventListener(SPA_HELLO_EVENT, onHello)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
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
    expect(getExpectedSpaVersion()).toBeNull()

    await act(async () => {
      MockWebSocket.instances[0]?.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({ type: 'spa_hello', spa_version: '0.5.4' }),
        }),
      )
    })

    expect(getExpectedSpaVersion()).toBe('0.5.4')
    expect(seen).toEqual(['0.5.4'])
    window.removeEventListener(SPA_HELLO_EVENT, onHello)
  })
})
