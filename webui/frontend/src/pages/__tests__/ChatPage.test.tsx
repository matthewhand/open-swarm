import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ChatPage, { chatLoginHref, chatLoginNext } from '../ChatPage'
import AgentSidebar from '../../components/AgentSidebar'
import { AGENT_CHAT_SESSIONS_KEY } from '../../lib/agentChatSessions'

type WsHandler = ((ev?: Event) => void) | null

class MockWebSocket {
  static OPEN = 1
  static CONNECTING = 0
  static instances: MockWebSocket[] = []

  readyState = MockWebSocket.CONNECTING
  url: string
  onopen: WsHandler = null
  onmessage: WsHandler = null
  onclose: WsHandler = null
  send = vi.fn()
  close = vi.fn(() => {
    this.readyState = 3
    this.onclose?.(new CloseEvent('close', { code: 1000 }))
  })

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

function renderChat(initialEntry = '/chat', { sidebar = false } = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        {sidebar ? <AgentSidebar /> : null}
        <ChatPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function mockAgentListFetch() {
  return vi.fn().mockImplementation(async (input: RequestInfo) => {
    const url = String(input)
    if (url.includes('/v1/support/context')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          object: 'support.context',
          briefing: '**Agents**\n- Support · support\n\n**Inference** off',
        }),
      } as Response
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({
        data: [
          {
            id: 'hybrid_team',
            name: 'Hybrid Team',
            description: 'Hybrid',
            object: 'blueprint',
          },
          {
            id: 'support',
            name: 'Support',
            description: 'Onboarding. First team.',
            role: 'support',
            object: 'blueprint',
          },
          {
            id: 'skeptic',
            name: 'Skeptic',
            description: 'Review',
            role: 'skeptic',
            object: 'blueprint',
          },
        ],
      }),
    } as Response
  })
}

async function openLatestSocket() {
  const ws = MockWebSocket.instances[MockWebSocket.instances.length - 1]
  await act(async () => {
    ws?.open()
  })
  return ws
}

function injectTurn(ws: MockWebSocket, user: string, assistant: string, id: string) {
  ws.onmessage?.(
    new MessageEvent('message', {
      data: `<div id="message-list" hx-swap-oob="beforeend"><div class="user-message">${user}</div></div>`,
    }),
  )
  ws.onmessage?.(
    new MessageEvent('message', {
      data: `<div id="message-list" hx-swap-oob="beforeend"><div id="message-response-${id}" class="assistant-message"></div></div>`,
    }),
  )
  ws.onmessage?.(
    new MessageEvent('message', {
      data: `<div id="message-response-${id}" hx-swap-oob="true" class="assistant-message">${assistant}</div>`,
    }),
  )
}

beforeEach(() => {
  localStorage.removeItem(AGENT_CHAT_SESSIONS_KEY)
})

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
  })

  it('disables send while connecting and announces status via aria-live', async () => {
    renderChat()

    const statusRegion = screen.getByRole('status', { name: 'Connection status' })
    expect(statusRegion).toHaveAttribute('aria-live', 'polite')
    expect(statusRegion).toHaveTextContent(/Connecting/i)

    const composer = screen.getByRole('textbox', { name: 'Chat message' })
    expect(composer).toBeDisabled()
    expect(composer).toHaveAttribute(
      'placeholder',
      expect.stringMatching(/Connecting/i),
    )
    expect(screen.getByRole('button', { name: /Send/i })).toBeDisabled()

    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    await waitFor(() => {
      expect(statusRegion).toHaveTextContent(/^Connected$/)
    })
    expect(composer).not.toBeDisabled()
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
    expect(screen.getByText(/REST API bearer token/i)).toBeInTheDocument()
    // Fixed-height chat column must not flex-shrink the Unavailable CTA away.
    const unavailableAlert = screen
      .getAllByRole('alert')
      .find((el) => /sign in required/i.test(el.textContent || ''))
    expect(unavailableAlert?.className).toMatch(/shrink-0/)
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

describe('ChatPage blueprint query-param honesty', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    Element.prototype.scrollIntoView = vi.fn()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('keeps an unknown ?blueprint= preselect and warns honestly', async () => {
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

    const select = await screen.findByRole('combobox', { name: 'Blueprint' })
    expect(select).toHaveValue('just_launched_team')
    expect(
      screen.getByRole('option', { name: /just_launched_team \(not in list\)/i }),
    ).toBeInTheDocument()

    const honesty = await screen.findByRole('alert')
    expect(honesty).toHaveTextContent(/not in the discoverable list/i)
    expect(honesty).toHaveTextContent('just_launched_team')
    expect(honesty).toHaveTextContent(/reply errors/i)
    expect(honesty).toHaveTextContent(/does not fall back to the default model/i)
  })

  it('does not warn when the ?blueprint= id is discoverable', async () => {
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

    const select = await screen.findByRole('combobox', { name: 'Blueprint' })
    expect(select).toHaveValue('codey')
    expect(screen.queryByText(/not in the discoverable list/i)).not.toBeInTheDocument()
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
  })

  it('defaults /chat to Support with a quiet system pill, not a transcript dump', async () => {
    const briefing =
      '**Agents**\n- Support · support\n\n**Inference** off\n\n**Gate** — dangerous tool call? yes/no. Until wired, all approved.\n**Skeptic** — prompt done? If not, findings go back to retry.'
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/v1/support/context')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              object: 'support.context',
              briefing,
              welcome: briefing,
              inference: { configured: false },
            }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({
            data: [
              { id: 'codey', name: 'Codey', description: 'Code' },
              {
                id: 'support',
                name: 'Support',
                description: 'Onboarding. First team.',
                role: 'support',
              },
            ],
          }),
        } as Response
      }),
    )

    renderChat('/chat')
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const select = await screen.findByRole('combobox', { name: 'Blueprint' })
    await waitFor(() => {
      expect(select).toHaveValue('support')
    })

    expect(screen.queryByTestId('chat-md')).not.toBeInTheDocument()
    expect(screen.queryByText('Connected and ready')).not.toBeInTheDocument()
    expect(screen.queryByText(/Welcome —/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Inference/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Gate/)).not.toBeInTheDocument()

    const pill = await screen.findByRole('button', { name: /System → Support/ })
    expect(pill).toHaveAttribute('aria-expanded', 'false')
    expect(pill).toHaveClass('os-handoff-chip--system')

    const newTeam = screen.getByRole('link', { name: 'New team' })
    expect(newTeam).toHaveAttribute('href', '/teams/launch/')
    expect(screen.getByRole('link', { name: 'Set inference' })).toHaveAttribute(
      'href',
      '/settings/',
    )
    expect(screen.getByRole('link', { name: 'Write blueprint' })).toHaveAttribute(
      'href',
      '/agent-creator/',
    )

    fireEvent.click(pill)
    expect(pill).toHaveAttribute('aria-expanded', 'true')
    const briefingEl = await screen.findByTestId('support-briefing')
    expect(briefingEl).toHaveTextContent(/Agents/)
    expect(briefingEl).toHaveTextContent(/Support/)
    expect(briefingEl).toHaveTextContent(/Inference/)
    expect(briefingEl).toHaveTextContent(/Gate/)
    expect(briefingEl).toHaveTextContent(/Skeptic/)
    expect(briefingEl.closest('.chat-bubble')).toBeNull()
    expect(screen.queryByTestId('chat-md')).not.toBeInTheDocument()
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

describe('ChatPage per-agent threads', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    Element.prototype.scrollIntoView = vi.fn()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.stubGlobal('fetch', mockAgentListFetch())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('keeps Support, hybrid_team, and skeptic transcripts isolated and restorable', async () => {
    renderChat('/chat', { sidebar: true })

    const select = await screen.findByRole('combobox', { name: 'Blueprint' })
    await waitFor(() => {
      expect(select).toHaveValue('support')
    })
    expect(screen.getByTestId('chat-agent-header')).toHaveTextContent('Support')
    expect(screen.getByRole('button', { name: /System → Support/ })).toBeInTheDocument()

    await openLatestSocket()
    const supportSocket = MockWebSocket.instances[MockWebSocket.instances.length - 1]!
    await act(async () => {
      injectTurn(supportSocket, 'hello support', 'support reply', 'sup1')
    })
    expect(screen.getByText('hello support')).toBeInTheDocument()
    expect(screen.getByText('support reply')).toBeInTheDocument()
    const supportUrl = supportSocket.url
    expect(supportUrl).toMatch(/\/ws\/ai-demo\/.+\/\?blueprint=support$/)

    fireEvent.click(screen.getByRole('link', { name: /Hybrid Team/ }))
    await waitFor(() => {
      expect(select).toHaveValue('hybrid_team')
    })
    expect(screen.getByTestId('chat-agent-header')).toHaveTextContent('Hybrid Team')
    expect(screen.queryByText('hello support')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /System → Support/ })).not.toBeInTheDocument()

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBeGreaterThan(1)
    })
    await openLatestSocket()
    const hybridSocket = MockWebSocket.instances[MockWebSocket.instances.length - 1]!
    expect(hybridSocket.url).not.toBe(supportUrl)
    expect(hybridSocket.url).toMatch(/\/ws\/ai-demo\/.+\/\?blueprint=hybrid_team$/)
    await act(async () => {
      injectTurn(hybridSocket, 'hello hybrid', 'hybrid reply', 'hyb1')
    })
    expect(screen.getByText('hello hybrid')).toBeInTheDocument()
    expect(screen.queryByText('hello support')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: /Skeptic/ }))
    await waitFor(() => {
      expect(select).toHaveValue('skeptic')
    })
    expect(screen.getByTestId('chat-agent-header')).toHaveTextContent('Skeptic')
    expect(screen.queryByText('hello hybrid')).not.toBeInTheDocument()
    expect(screen.queryByText('hello support')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: /^Support/ }))
    await waitFor(() => {
      expect(select).toHaveValue('support')
    })
    expect(screen.getByText('hello support')).toBeInTheDocument()
    expect(screen.getByText('support reply')).toBeInTheDocument()
    expect(screen.queryByText('hello hybrid')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /System → Support/ })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: /Hybrid Team/ }))
    await waitFor(() => {
      expect(screen.getByText('hello hybrid')).toBeInTheDocument()
    })
    expect(screen.queryByText('hello support')).not.toBeInTheDocument()
  })

  it('restores an agent thread after remount from the persisted session', async () => {
    const { unmount } = renderChat('/chat?blueprint=support')
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: 'Blueprint' })).toHaveValue('support')
    })
    await openLatestSocket()
    await act(async () => {
      injectTurn(
        MockWebSocket.instances[MockWebSocket.instances.length - 1]!,
        'remember this',
        'stored for support',
        'persist1',
      )
    })
    expect(screen.getByText('remember this')).toBeInTheDocument()
    unmount()

    MockWebSocket.instances = []
    renderChat('/chat?blueprint=support')
    expect(await screen.findByText('remember this')).toBeInTheDocument()
    expect(screen.getByText('stored for support')).toBeInTheDocument()
    expect(screen.getByTestId('chat-agent-header')).toHaveTextContent('Support')
  })
})
