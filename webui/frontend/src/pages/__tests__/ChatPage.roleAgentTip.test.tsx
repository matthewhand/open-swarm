import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ChatPage from '../ChatPage'
import { ToastProvider } from '../../components/DaisyUI'
import { resetConversationThreads } from '../../lib/chatMeter'
import { ROLE_AGENT_TIP_STORAGE_KEY, ROLE_AGENT_TIP_TITLE } from '../../lib/roleAgentTip'

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

function stubFetch(agents: Array<{ id: string; name: string; role?: string }>) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(async (input: RequestInfo) => {
      const url = String(input)
      if (url.includes('/v1/preferences')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            object: 'user_preferences',
            principal: 'session:test',
            guest: true,
            empty: true,
            favourites: [],
            hidden_agents: [],
            hostname_override: '',
            values: {},
          }),
        } as Response
      }
      if (url.includes('/suggestions/')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ object: 'suggestions', suggestions: [] }),
        } as Response
      }
      if (url.includes('/settings/')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            agent_id: agents[0]?.id || 'support',
            new_chat_per_task: false,
            use_suggestions: false,
          }),
        } as Response
      }
      if (url.includes('/chat/thread/')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            agent_id: agents[0]?.id || 'support',
            conversation_id: 'conv-tip',
            messages: [],
          }),
        } as Response
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ data: agents }),
      } as Response
    }),
  )
}

function renderChat(entry = '/chat') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={[entry]}>
          <ChatPage />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

describe('ChatPage REQ-191 role-agent tip', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    window.localStorage.clear()
    Element.prototype.scrollIntoView = vi.fn()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
    resetConversationThreads()
  })

  async function openChat(entry: string, agents: Array<{ id: string; name: string; role?: string }>) {
    stubFetch(agents)
    renderChat(entry)
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })
  }

  it('shows the tip when chatting with a role agent', async () => {
    await openChat('/chat?blueprint=support', [
      { id: 'support', name: 'Support', role: 'support' },
    ])
    expect(await screen.findByTestId('role-agent-tip')).toBeInTheDocument()
    expect(screen.getByText(ROLE_AGENT_TIP_TITLE)).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Chat message' })).toBeInTheDocument()
    expect(screen.getByTestId('chat-messages-container')).toBeInTheDocument()
  })

  it('does not show the tip for a role-less agent', async () => {
    await openChat('/chat?blueprint=codey', [{ id: 'codey', name: 'Codey' }])
    await screen.findByRole('textbox', { name: 'Chat message' })
    expect(screen.queryByTestId('role-agent-tip')).not.toBeInTheDocument()
  })

  it('dismiss click hides the tip, persists, and keeps chat mounted', async () => {
    await openChat('/chat?blueprint=gate', [{ id: 'gate', name: 'Safety', role: 'gate' }])
    expect(await screen.findByTestId('role-agent-tip')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('role-agent-tip-dismiss'))
    await waitFor(() => {
      expect(screen.queryByTestId('role-agent-tip')).not.toBeInTheDocument()
    })
    expect(localStorage.getItem(ROLE_AGENT_TIP_STORAGE_KEY)).toBe('1')
    expect(screen.getByRole('textbox', { name: 'Chat message' })).toBeInTheDocument()
    expect(screen.getByTestId('chat-messages-container')).toBeInTheDocument()
  })

  it('Esc dismisses the tip without unmounting chat or clearing a draft', async () => {
    await openChat('/chat?blueprint=skeptic', [
      { id: 'skeptic', name: 'Skeptic', role: 'skeptic' },
    ])
    const composer = await screen.findByRole('textbox', { name: 'Chat message' })
    expect(await screen.findByTestId('role-agent-tip')).toBeInTheDocument()
    fireEvent.change(composer, { target: { value: 'keep this draft' } })
    fireEvent.keyDown(composer, { key: 'Escape' })
    await waitFor(() => {
      expect(screen.queryByTestId('role-agent-tip')).not.toBeInTheDocument()
    })
    expect(composer).toHaveValue('keep this draft')
    expect(screen.getByTestId('chat-messages-container')).toBeInTheDocument()
  })

  it('stays hidden after a persisted dismiss on remount', async () => {
    localStorage.setItem(ROLE_AGENT_TIP_STORAGE_KEY, '1')
    await openChat('/chat?blueprint=support', [
      { id: 'support', name: 'Support', role: 'support' },
    ])
    await screen.findByRole('textbox', { name: 'Chat message' })
    expect(screen.queryByTestId('role-agent-tip')).not.toBeInTheDocument()
  })
})
