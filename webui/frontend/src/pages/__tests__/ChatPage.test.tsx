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
    expect(screen.getByRole('menuitem', { name: 'Blueprints' })).toHaveAttribute(
      'href',
      '/blueprint-library/',
    )
    expect(screen.getByRole('menuitem', { name: 'Teams' })).toHaveAttribute('href', '/teams/launch/')
    expect(screen.getByRole('menuitem', { name: 'Settings' })).toHaveAttribute('href', '/settings/')
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
      const userFrames = ws.send.mock.calls
        .map((call) => JSON.parse(String(call[0])))
        .filter((frame) => frame.message && frame.type !== 'status')
      expect(userFrames).toHaveLength(2)
      expect(userFrames[1]).toEqual({
        message: 'just codey',
        params: { team: 'demo-team', target: 'codey' },
      })
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

describe('ChatPage dropdown status lines (REQ-46)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
  })

  function stubWithThreadStore(store: { messages: { role: string; content: string }[] }) {
    MockWebSocket.instances = []
    Element.prototype.scrollIntoView = vi.fn()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input)
        if (url.includes('/chat/thread/')) {
          if (init?.method === 'POST') {
            const body = JSON.parse(String(init.body || '{}')) as {
              message?: { role?: string; content?: string }
            }
            if (body.message?.role && body.message.content) {
              store.messages.push({
                role: body.message.role,
                content: body.message.content,
              })
            }
          }
          return {
            ok: true,
            status: 200,
            json: async () => ({
              agent_id: 'team-demo-team',
              conversation_id: 'team-demo-team',
              messages: store.messages,
            }),
          } as Response
        }
        if (url.includes('team_rosters') || url.includes('team-rosters')) {
          return {
            ok: true,
            status: 200,
            json: async () => DEMO_ROSTER,
          } as Response
        }
        if (url.includes('/v1/cli-agents')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ clis: ['antigravity', 'grok'] }),
          } as Response
        }
        if (url.includes('/v1/models')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              data: [
                { id: 'gpt-4', object: 'model', created: 0, owned_by: 'openai' },
                { id: 'grok-4', object: 'model', created: 0, owned_by: 'xai' },
              ],
            }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({
            data: [{ id: 'cli_agent', name: 'CLI agent', description: 'CLI' }],
          }),
        } as Response
      }),
    )
  }

  it('appends one team-target status event that is not a bubble and survives reload', async () => {
    const store = { messages: [] as { role: string; content: string }[] }
    stubWithThreadStore(store)

    const first = renderChat('/chat?team=demo-team')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    fireEvent.change(await screen.findByRole('combobox', { name: 'Team members' }), {
      target: { value: 'codey' },
    })

    const status = await screen.findByTestId('chat-status')
    expect(status).toHaveTextContent('Team target: All members → Codey (agent/coder)')
    expect(status).toHaveClass('os-chat-status')
    expect(status.className).not.toMatch(/chat-start|chat-end/)
    expect(status.querySelector('.chat-bubble')).toBeNull()
    expect(screen.getAllByTestId('chat-status')).toHaveLength(1)
    expect(store.messages).toHaveLength(1)
    expect(store.messages[0]).toEqual({
      role: 'status',
      content: 'Team target: All members → Codey (agent/coder)',
    })

    first.unmount()
    renderChat('/chat?team=demo-team')
    await act(async () => {
      MockWebSocket.instances[MockWebSocket.instances.length - 1]?.open()
    })

    const restored = await screen.findByTestId('chat-status')
    expect(restored).toHaveTextContent('Team target: All members → Codey (agent/coder)')
    expect(restored.className).not.toMatch(/chat-start|chat-end/)
    expect(screen.getAllByTestId('chat-status')).toHaveLength(1)
  })

  it('appends one CLI status event (antigravity → grok) that is not a bubble', async () => {
    const store = { messages: [] as { role: string; content: string }[] }
    stubWithThreadStore(store)

    renderChat('/chat?blueprint=cli_agent&mode=cli&cli=antigravity')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    fireEvent.change(await screen.findByRole('combobox', { name: 'CLI' }), {
      target: { value: 'grok' },
    })

    const status = await screen.findByTestId('chat-status')
    expect(status).toHaveTextContent('CLI: antigravity → grok')
    expect(status.className).not.toMatch(/chat-start|chat-end/)
    expect(status.querySelector('.chat-bubble')).toBeNull()
    expect(screen.getAllByTestId('chat-status')).toHaveLength(1)
  })
})
