import { act, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '../../components/DaisyUI'
import ChatPage from '../ChatPage'

class MockWebSocket {
  static OPEN = 1
  static CONNECTING = 0
  static instances: MockWebSocket[] = []
  readyState = MockWebSocket.CONNECTING
  onopen: ((ev?: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
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

function renderChat(initialEntry = '/chat?blueprint=cli_agent') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <ChatPage />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

describe('REQ-213 ChatPage compacted-card context menu', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    Element.prototype.scrollIntoView = vi.fn()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('right-click Prior history pill opens menu; Remove hides it and leaves later turns', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/chat/thread/')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              agent_id: 'cli_agent',
              conversation_id: 'cli-cli_agent-abc',
              messages: [
                {
                  role: 'system',
                  content: '**User:** old question\n\n**Assistant:** old answer',
                  kind: 'prior_history',
                },
                { role: 'user', content: 'from cli' },
              ],
            }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({
            data: [{ id: 'cli_agent', name: 'CLI Agent', description: 'CLI' }],
          }),
        } as Response
      }),
    )

    renderChat('/chat?blueprint=cli_agent&session=cli-cli_agent-abc')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const pill = await screen.findByRole('button', { name: /Prior history/i })
    fireEvent.contextMenu(pill)
    const menu = await screen.findByTestId('compacted-card-context-menu')
    expect(menu).toHaveClass('menu')
    expect(screen.getByRole('menuitem', { name: 'Expand' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('menuitem', { name: 'Remove from view' }))
    expect(screen.queryByRole('button', { name: /Prior history/i })).not.toBeInTheDocument()
    expect(screen.getByText('from cli')).toBeInTheDocument()
  })

  it('right-click Compact summary chip can Collapse then Expand without dropping the digest', async () => {
    const compactPayload = {
      summary: {
        id: 1,
        conversation_id: 'c-compact',
        span: { start: 0, end: 1 },
        parent_summary_id: null,
        body: 'outer digest',
        created_at: '2026-09-03T00:00:00Z',
        replaced_count: 2,
      },
      summaries: [
        {
          id: 1,
          conversation_id: 'c-compact',
          span: { start: 0, end: 1 },
          parent_summary_id: null,
          body: 'outer digest',
          created_at: '2026-09-03T00:00:00Z',
          replaced_count: 2,
        },
      ],
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input)
        if (url.includes('/chat/compact/') && init?.method === 'POST') {
          return { ok: true, status: 200, json: async () => compactPayload } as Response
        }
        if (url.includes('/chat/thread/')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              agent_id: 'jeeves',
              conversation_id: 'c-compact',
              messages: [
                { role: 'user', content: 'prior question' },
                { role: 'assistant', content: 'prior answer' },
              ],
              summaries: [],
            }),
          } as Response
        }
        return { ok: true, status: 200, json: async () => ({ data: [] }) } as Response
      }),
    )

    renderChat('/chat?blueprint=jeeves')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })
    expect(await screen.findByText('prior question')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Add' }))
    await act(async () => {
      fireEvent.click(screen.getByRole('menuitem', { name: 'Compact' }))
    })

    const card = await screen.findByTestId('chat-summary')
    expect(screen.getByText('outer digest')).toBeInTheDocument()
    fireEvent.contextMenu(card)
    fireEvent.click(screen.getByRole('menuitem', { name: 'Collapse' }))
    expect(screen.queryByText('outer digest')).not.toBeInTheDocument()
    fireEvent.contextMenu(screen.getByTestId('chat-summary'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Expand' }))
    expect(screen.getByText('outer digest')).toBeInTheDocument()
  })
})
