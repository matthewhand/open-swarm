import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useSearchParams } from 'react-router-dom'
import ChatPage from '../ChatPage'
import { ToastProvider } from '../../components/DaisyUI'
import { resetConversationThreads } from '../../lib/chatMeter'

const GH = 'https://github.com/matthewhand/open-swarm/pull/416'

type WsHandler = ((ev?: Event) => void) | null

class MockWebSocket {
  static OPEN = 1
  static CONNECTING = 0
  static instances: MockWebSocket[] = []

  readyState = MockWebSocket.CONNECTING
  onopen: WsHandler = null
  onmessage: WsHandler = null
  onclose: WsHandler = null
  send = vi.fn()
  close = vi.fn()
  url: string

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  open() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.(new Event('open'))
  }
}

function SearchProbe() {
  const [params] = useSearchParams()
  return <div data-testid="search-probe">{params.toString()}</div>
}

function renderChat(initialEntry = '/chat?blueprint=codey') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <SearchProbe />
          <Routes>
            <Route path="/chat" element={<ChatPage />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

function prPayload(opener: Record<string, unknown>) {
  return {
    type: 'pr_opened',
    url: GH,
    number: 416,
    title: 'REQ-71: PR-opened card',
    branch: 'cursor/req-71',
    additions: 5,
    deletions: 1,
    opener,
  }
}

describe('ChatPage REQ-71 PR-opened card', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    window.localStorage.clear()
    Element.prototype.scrollIntoView = vi.fn()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/chat/thread/')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              agent_id: 'codey',
              conversation_id: 'conv-codey',
              messages: [],
            }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({
            data: [
              { id: 'codey', name: 'Codey', description: 'Coder' },
              { id: 'support', name: 'Support', description: 'Support' },
            ],
          }),
        } as Response
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
    resetConversationThreads()
  })

  async function openOn(entry: string) {
    renderChat(entry)
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })
    return MockWebSocket.instances[0]!
  }

  it('same-agent same-thread: card with View PR and zero jump controls', async () => {
    const ws = await openOn('/chat?blueprint=codey')
    await act(async () => {
      ws.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify(prPayload({ agent_id: 'codey', name: 'Codey' })),
        }),
      )
    })
    const card = await screen.findByTestId('pr-opened-card')
    expect(card).toHaveClass('card')
    expect(screen.getByTestId('pr-opened-view')).toHaveAttribute('href', GH)
    expect(screen.getByTestId('pr-opened-title')).toHaveTextContent('REQ-71: PR-opened card')
    expect(screen.queryByTestId('pr-opened-jump')).not.toBeInTheDocument()
    expect(card.textContent).not.toMatch(/Open in Cursor/i)
    expect(card.textContent).not.toMatch(/Cursor/)
  })

  it('cross-agent: View PR plus avatar+name jump selects the opener thread', async () => {
    const ws = await openOn('/chat?blueprint=support')
    await act(async () => {
      ws.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify(
            prPayload({ agent_id: 'codey', name: 'Codey', conversation_id: 'conv-codey' }),
          ),
        }),
      )
    })
    expect(await screen.findByTestId('pr-opened-view')).toHaveAttribute('href', GH)
    const jump = screen.getByTestId('pr-opened-jump')
    expect(jump).toHaveTextContent('Codey')
    expect(jump).not.toHaveTextContent('Open in Cursor')
    fireEvent.click(jump)
    expect(screen.getByTestId('search-probe')).toHaveTextContent('blueprint=codey')
    expect(screen.getByTestId('search-probe')).toHaveTextContent('session=conv-codey')
  })

  it('malformed PR URL never invents View PR', async () => {
    const ws = await openOn('/chat?blueprint=codey')
    await act(async () => {
      ws.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'pr_opened',
            url: 'https://example.com/pull/9',
            number: 9,
            title: 'Not GitHub',
            opener: { agent_id: 'codey', conversation_id: 'conv-codey' },
          }),
        }),
      )
    })
    expect(await screen.findByTestId('pr-opened-card')).toBeInTheDocument()
    expect(screen.queryByTestId('pr-opened-view')).not.toBeInTheDocument()
  })
})

describe('ChatPage REQ-71 hydrate from persisted status JSON', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    window.localStorage.clear()
    Element.prototype.scrollIntoView = vi.fn()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/chat/thread/')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              agent_id: 'support',
              conversation_id: 'conv-support',
              messages: [
                {
                  role: 'status',
                  content: JSON.stringify({
                    type: 'pr_opened',
                    url: GH,
                    number: 416,
                    title: 'Hydrated card',
                    opener: { agent_id: 'codey', name: 'Codey', conversation_id: 'conv-codey' },
                  }),
                },
              ],
            }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({
            data: [
              { id: 'codey', name: 'Codey' },
              { id: 'support', name: 'Support' },
            ],
          }),
        } as Response
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
    resetConversationThreads()
  })

  it('restores a card with View PR and jump when the opener is another agent', async () => {
    renderChat('/chat?blueprint=support')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })
    expect(await screen.findByTestId('pr-opened-card')).toBeInTheDocument()
    expect(screen.getByTestId('pr-opened-title')).toHaveTextContent('Hydrated card')
    expect(screen.getByTestId('pr-opened-view')).toHaveAttribute('href', GH)
    expect(screen.getByTestId('pr-opened-jump')).toHaveTextContent('Codey')
    expect(screen.queryByText(/\{"type":"pr_opened"/)).not.toBeInTheDocument()
  })
})
