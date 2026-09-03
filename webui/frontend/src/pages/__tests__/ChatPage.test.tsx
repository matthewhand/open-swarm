import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ChatPage, { chatLoginHref, chatLoginNext } from '../ChatPage'
import { ToastProvider } from '../../components/DaisyUI'
import { resetConversationThreads } from '../../lib/chatMeter'

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
  close = vi.fn(() => {
    this.readyState = 3
    this.onclose?.(new CloseEvent('close', { code: 1000 }))
  })

  url: string

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  open() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.(new Event('open'))
  }

  /** Simulate handshake/network failure before onopen (opaque browser 1006). */
  failBeforeOpen(code = 1006) {
    this.readyState = 3
    this.onclose?.(new CloseEvent('close', { code }))
  }

  /** Simulate DjangoChatConsumer auth gate (accept then close 4401). */
  rejectAuth() {
    this.open()
    this.readyState = 3
    this.onclose?.(
      new CloseEvent('close', { code: 4401, reason: 'authentication required' }),
    )
  }
}

function renderChat(initialEntry = '/chat') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
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

describe('chatLoginHref helpers', () => {
  it('builds a rooted next path and encodes the Sign-in CTA', () => {
    expect(chatLoginNext(new URLSearchParams())).toBe('/chat')
    expect(chatLoginNext(new URLSearchParams('blueprint=codey'))).toBe(
      '/chat?blueprint=codey',
    )
    expect(chatLoginHref(new URLSearchParams('blueprint=codey'))).toBe(
      `/accounts/login/?next=${encodeURIComponent('/chat?blueprint=codey')}`,
    )
  })
})

describe('ChatPage reconnect focus', () => {
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
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetConversationThreads()
  })

  it('does not auto-focus the composer on the initial connect', async () => {
    renderChat()
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const composer = await screen.findByRole('textbox', { name: 'Chat message' })
    expect(composer).not.toHaveFocus()
    expect(composer).not.toBeDisabled()
  })

  it('moves focus to the composer after a successful reconnect', async () => {
    renderChat()

    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })
    // Drop the socket so the reconnect CTA appears.
    await act(async () => {
      MockWebSocket.instances[0]?.close()
    })

    const reconnect = await screen.findByRole('button', { name: /Reconnect/i })
    fireEvent.click(reconnect)

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(2)
    })
    await act(async () => {
      MockWebSocket.instances[MockWebSocket.instances.length - 1]?.open()
    })

    const composer = await screen.findByRole('textbox', { name: 'Chat message' })
    await waitFor(() => {
      expect(composer).not.toBeDisabled()
    })
    expect(composer).toHaveFocus()
  })
})

describe('ChatPage Unavailable / Sign-in CTA + connection status', () => {
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
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetConversationThreads()
  })

  it('disables send while connecting and stays silent when healthy', async () => {
    renderChat()

    const statusRegion = screen.getByRole('status', { name: 'Connection status' })
    expect(statusRegion).toHaveAttribute('aria-live', 'polite')
    expect(statusRegion).toHaveTextContent(/Connecting/i)

    const composer = screen.getByRole('textbox', { name: 'Chat message' })
    expect(composer).toBeDisabled()
    expect(composer).toHaveAttribute('placeholder', 'Message …')
    expect(screen.getByRole('button', { name: /Send/i })).toBeDisabled()
    expect(screen.queryByText(/^Connected$/)).not.toBeInTheDocument()

    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    await waitFor(() => {
      expect(composer).not.toBeDisabled()
    })
    expect(screen.queryByText(/^Connected$/)).not.toBeInTheDocument()
    expect(statusRegion).toHaveTextContent('')
  })

  it('shows session-cookie Sign-in CTA when the server closes with 4401', async () => {
    renderChat('/chat?blueprint=hybrid_team')

    await act(async () => {
      MockWebSocket.instances[0]?.rejectAuth()
    })

    const signIn = await screen.findByRole('link', { name: /Sign in/i })
    expect(signIn).toHaveAttribute(
      'href',
      `/accounts/login/?next=${encodeURIComponent('/chat?blueprint=hybrid_team')}`,
    )
    expect(screen.getByRole('button', { name: /Reconnect/i })).toBeInTheDocument()
    const statusRegion = screen.getByRole('status', { name: 'Connection status' })
    expect(statusRegion).toHaveTextContent(/Unavailable — sign in required/i)
    expect(screen.getByText(/session cookie/i)).toBeInTheDocument()
  })

  it('does not blame login when the socket never opens (ASGI/network)', async () => {
    renderChat()

    await act(async () => {
      MockWebSocket.instances[0]?.failBeforeOpen()
    })

    expect(
      await screen.findByText(/Unavailable — websocket unreachable/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/ALLOWED_HOSTS/i)).toBeInTheDocument()
    expect(screen.queryByText(/session cookie/i)).not.toBeInTheDocument()
  })

  it('clears the composer draft on Escape', async () => {
    renderChat()
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const composer = await screen.findByRole('textbox', { name: 'Chat message' })
    fireEvent.change(composer, { target: { value: 'draft that should clear' } })
    expect(composer).toHaveValue('draft that should clear')

    fireEvent.keyDown(composer, { key: 'Escape' })
    expect(composer).toHaveValue('')
  })
})

describe('ChatPage agent header (no blueprint dropdown)', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    Element.prototype.scrollIntoView = vi.fn()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetConversationThreads()
  })

  it('uses the ?blueprint= id as the chat header without a catalog dropdown', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          data: [{ id: 'codey', name: 'Codey', description: 'Code assistant' }],
        }),
      } as Response),
    )

    renderChat('/chat?blueprint=just_launched_team')

    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    expect(await screen.findByRole('heading', { name: 'just_launched_team' })).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Blueprint' })).not.toBeInTheDocument()
  })

  it('shows the discoverable agent name in the header', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          data: [{ id: 'codey', name: 'Codey', description: 'Code assistant' }],
        }),
      } as Response),
    )

    renderChat('/chat?blueprint=codey')

    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    expect(await screen.findByRole('heading', { name: 'Codey' })).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Blueprint' })).not.toBeInTheDocument()
  })
})

describe('ChatPage Send button honesty while streaming', () => {
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
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetConversationThreads()
  })

  it('keeps a real Send control (no busy spinner) while an assistant reply streams', async () => {
    renderChat()
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const ws = MockWebSocket.instances[0]!
    await act(async () => {
      ws.onmessage?.(
        new MessageEvent('message', {
          data: '<div id="message-list" hx-swap-oob="beforeend"><div id="message-response-abc123" class="assistant-message"></div></div>',
        }),
      )
    })

    const send = screen.getByRole('button', { name: /^Send$/i })
    expect(send).not.toHaveAttribute('aria-busy', 'true')

    const loaders = screen.getAllByRole('status', { name: 'Loading' })
    expect(loaders.length).toBeGreaterThan(0)
  })
})

describe('ChatPage auto-reconnect backoff', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    Element.prototype.scrollIntoView = vi.fn()
    vi.useFakeTimers({ shouldAdvanceTime: true })
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
    vi.useRealTimers()
    vi.unstubAllGlobals()
    resetConversationThreads()
  })

  it('reconnects with backoff after unexpected drop, and skips auth 4401', async () => {
    renderChat()
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    await act(async () => {
      const ws = MockWebSocket.instances[0]!
      ws.readyState = 3
      ws.onclose?.(new CloseEvent('close', { code: 1006 }))
    })

    expect(MockWebSocket.instances).toHaveLength(1)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(2)

    // Auth gate must not auto-reconnect.
    const authClient = MockWebSocket.instances.length
    await act(async () => {
      MockWebSocket.instances[MockWebSocket.instances.length - 1]?.rejectAuth()
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(MockWebSocket.instances.length).toBe(authClient)
  })
})

describe('ChatPage computer-control stub (REQ-27b)', () => {
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
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a top-right Computer control tool by default (not agent-attached)', async () => {
    renderChat()
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const tools = screen.getByRole('toolbar', { name: 'Chat tools' })
    const trigger = screen.getByRole('button', { name: 'Computer control' })
    expect(tools).toContainElement(trigger)

    fireEvent.click(trigger)
    const dialog = screen.getByRole('dialog', { name: 'Computer control', hidden: true })
    expect(dialog).toHaveClass('modal-open')
    expect(dialog).toHaveTextContent(/^[\s\S]*WIP[\s\S]*OMB or Rakazo remote/)
    expect(dialog).toHaveTextContent(/not implemented here/i)
  })
})

describe('ChatPage markdown bubbles', () => {
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
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetConversationThreads()
  })

  it('renders assistant markdown (bold/code) in the bubble', async () => {
    renderChat()
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const ws = MockWebSocket.instances[0]!
    await act(async () => {
      ws.onmessage?.(
        new MessageEvent('message', {
          data: '<div id="message-list" hx-swap-oob="beforeend"><div id="message-response-md1" class="assistant-message"></div></div>',
        }),
      )
      ws.onmessage?.(
        new MessageEvent('message', {
          data: '<div id="message-response-md1" hx-swap-oob="true" class="assistant-message">**hello** and `code`</div>',
        }),
      )
    })

    expect(screen.getByText('hello').tagName).toBe('STRONG')
    expect(screen.getByText('code').tagName).toBe('CODE')
  })
})

describe('ChatPage per-agent persistence (no retention chrome)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
  })

  it('restores a persisted agent thread after load and keeps retention off the chrome', async () => {
    MockWebSocket.instances = []
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
              agent_id: 'jeeves',
              conversation_id: 'agt-1-jeeves',
              messages: [
                { role: 'user', content: 'prior question' },
                { role: 'assistant', content: 'prior answer' },
              ],
            }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({
            data: [{ id: 'jeeves', name: 'Jeeves', description: 'Butler' }],
          }),
        } as Response
      }),
    )

    renderChat('/chat?blueprint=jeeves')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    expect(await screen.findByText('prior question')).toBeInTheDocument()
    expect(screen.getByText('prior answer')).toBeInTheDocument()
    expect(screen.queryByText(/Move to trash/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Empty trash/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Disk used/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /archive/i })).not.toBeInTheDocument()
  })

  it('renders a CLI session notice without a chat-start/chat-end bubble', async () => {
    MockWebSocket.instances = []
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
              agent_id: 'cli_agent',
              conversation_id: 'agt-1-cli',
              messages: [
                { role: 'user', content: 'hello' },
                { role: 'status', content: 'Started a new grok session.' },
                { role: 'assistant', content: 'hi' },
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

    renderChat('/chat?blueprint=cli_agent')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const notice = await screen.findByText('Started a new grok session.')
    expect(notice).toHaveAttribute('data-role', 'status')
    expect(notice.closest('.chat-start')).toBeNull()
    expect(notice.closest('.chat-end')).toBeNull()
    expect(notice.closest('.chat-bubble')).toBeNull()
  })
})

describe('ChatPage Grok composer and per-agent threads', () => {
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
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    resetConversationThreads()
  })

  it('uses a pill composer with + operator menu and mic', async () => {
    renderChat()
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    expect(screen.getByRole('textbox', { name: 'Chat message' })).toHaveAttribute(
      'placeholder',
      'Message …',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))
    expect(screen.getByRole('menuitem', { name: 'Compact' })).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Blueprints' })).not.toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Teams' })).not.toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Settings' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Open settings' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Voice input' })).toBeInTheDocument()
    expect(screen.getByLabelText('Tokens in context')).toBeInTheDocument()
  })

  it('opens a unique websocket thread per agent', async () => {
    const first = renderChat('/chat?blueprint=codey')
    expect(MockWebSocket.instances[0]?.url).toContain('/ws/ai-demo/')
    const codeyUrl = MockWebSocket.instances[0]!.url
    first.unmount()

    renderChat('/chat?blueprint=stewie')
    const stewieUrl = MockWebSocket.instances[MockWebSocket.instances.length - 1]!.url
    expect(stewieUrl).toContain('/ws/ai-demo/')
    expect(stewieUrl).not.toBe(codeyUrl)
  })

  it('renders a bordered Summary block after Compact (nested parent stays inside)', async () => {
    const compactPayload = {
      summary: {
        id: 2,
        conversation_id: 'c-compact',
        span: { start: 0, end: 1 },
        parent_summary_id: 1,
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
          body: 'inner digest',
          created_at: '2026-09-03T00:00:00Z',
          replaced_count: 2,
        },
        {
          id: 2,
          conversation_id: 'c-compact',
          span: { start: 0, end: 1 },
          parent_summary_id: 1,
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
          return {
            ok: true,
            status: 200,
            json: async () => compactPayload,
          } as Response
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
        return {
          ok: true,
          status: 200,
          json: async () => ({ data: [] }),
        } as Response
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

    const blocks = await screen.findAllByTestId('chat-summary')
    expect(blocks.length).toBe(2)
    expect(blocks[0]).toHaveClass('chat-summary')
    expect(blocks[1]).toHaveClass('chat-summary')
    expect(blocks[1]).toHaveClass('chat-summary--nested')
    expect(screen.getAllByText('Summary').length).toBe(2)
    expect(screen.getByText('outer digest')).toBeInTheDocument()
    expect(screen.getByText('inner digest')).toBeInTheDocument()
    expect(screen.queryByText('prior question')).not.toBeInTheDocument()
  })
})

const DEMO_ROSTER = {
  object: 'list',
  data: [
    {
      id: 'demo-team',
      object: 'team_roster',
      name: 'Demo Team',
      description: 'Example multi-agent roster',
      members: [
        { id: 'codey', name: 'Codey', kind: 'agent', role: 'coder' },
        { id: 'stewie', name: 'Stewie', kind: 'agent', role: 'ops' },
      ],
    },
  ],
}

function stubTeamAndBlueprints() {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(async (input: RequestInfo) => {
      const url = String(input)
      if (url.includes('team_rosters') || url.includes('team-rosters')) {
        return {
          ok: true,
          status: 200,
          json: async () => DEMO_ROSTER,
        } as Response
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({
          data: [{ id: 'codey', name: 'Codey', description: 'Code assistant' }],
        }),
      } as Response
    }),
  )
}

describe('ChatPage team member dropdown', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    Element.prototype.scrollIntoView = vi.fn()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    stubTeamAndBlueprints()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('lists All members first, then name + kind/role, then Manage Teams (unlabeled)', async () => {
    renderChat('/chat?team=demo-team')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const select = await screen.findByRole('combobox')
    expect(select).not.toHaveAccessibleName('Blueprint')
    const options = within(select).getAllByRole('option')
    expect(options.map((opt) => opt.textContent)).toEqual([
      'All members',
      'Codey (agent/coder)',
      'Stewie (agent/ops)',
      'Manage Teams',
    ])
    expect(select).toHaveValue('all')
    expect(screen.queryByText('Blueprint')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Demo Team' })).toBeInTheDocument()
  })

  it('sends params {team, target} for all-members and a chosen member', async () => {
    renderChat('/chat?team=demo-team')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const composer = await screen.findByRole('textbox', { name: 'Chat message' })
    fireEvent.change(composer, { target: { value: 'hello team' } })
    fireEvent.click(screen.getByRole('button', { name: /^Send$/i }))

    const ws = MockWebSocket.instances[0]!
    await waitFor(() => {
      expect(ws.send).toHaveBeenCalled()
    })
    expect(JSON.parse(String(ws.send.mock.calls[0][0]))).toEqual({
      message: 'hello team',
      params: { team: 'demo-team', target: 'all' },
    })

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'codey' } })
    fireEvent.change(composer, { target: { value: 'just codey' } })
    fireEvent.click(screen.getByRole('button', { name: /^Send$/i }))

    await waitFor(() => {
      expect(ws.send).toHaveBeenCalledTimes(2)
    })
    expect(JSON.parse(String(ws.send.mock.calls[1][0]))).toEqual({
      message: 'just codey',
      params: { team: 'demo-team', target: 'codey' },
    })
  })

  it('keeps Manage Teams last and does not send when that item is chosen', async () => {
    renderChat('/chat?team=demo-team')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const select = await screen.findByRole('combobox')
    const options = within(select).getAllByRole('option')
    expect(options[options.length - 1]).toHaveValue('__manage__')
    expect(options[options.length - 1]).toHaveTextContent('Manage Teams')
    expect(select).toHaveValue('all')
    expect(MockWebSocket.instances[0]!.send).not.toHaveBeenCalled()
  })
})
