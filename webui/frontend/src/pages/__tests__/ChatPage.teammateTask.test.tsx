import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ChatPage from '../ChatPage'
import { ToastProvider } from '../../components/DaisyUI'
import { resetConversationThreads } from '../../lib/chatMeter'

const HERMES_UI = 'http://127.0.0.1:9119/stub-hermes'
const GH = 'https://github.com/matthewhand/open-swarm/pull/416'
const OMB_WORD = /\bOMB\b/

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

const HARNESS_ROSTER = {
  object: 'list',
  data: [
    {
      id: 'harness-team',
      object: 'team_roster',
      name: 'Harness Team',
      members: [
        { id: 'hermes', name: 'Hermes', kind: 'remote', role: 'default' },
        { id: 'omb', name: 'OpenMousBot', kind: 'remote', role: 'default' },
      ],
    },
  ],
}

const LOCAL_ROSTER = {
  object: 'list',
  data: [
    {
      id: 'local-team',
      object: 'team_roster',
      name: 'Local Team',
      members: [{ id: 'codey', name: 'Codey', kind: 'api', role: 'default' }],
    },
  ],
}

const HERMES_REMOTES = {
  object: 'list',
  kinds: [
    { id: 'hermes', label: 'Hermes' },
    { id: 'omb', label: 'OpenMousBot' },
  ],
  configured: [
    {
      id: 'hermes',
      kind: 'hermes',
      label: 'Hermes',
      title: 'Hermes',
      base_url: 'http://127.0.0.1:8642',
      ui_url: HERMES_UI,
      source: 'config',
    },
  ],
  data: [],
}

const EMPTY_REMOTES = {
  object: 'list',
  kinds: [{ id: 'hermes', label: 'Hermes' }],
  configured: [
    {
      id: 'hermes',
      kind: 'hermes',
      label: 'Hermes',
      title: 'Hermes',
      base_url: '',
      ui_url: '',
      source: 'config',
    },
  ],
  data: [],
}

function renderChat(initialEntry: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Routes>
            <Route path="/chat" element={<ChatPage />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

function mockFetch(opts: { roster?: unknown; remotes?: unknown; threadMessages?: unknown[] }) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(async (input: RequestInfo) => {
      const url = String(input)
      if (url.includes('/chat/thread/')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            agent_id: 'team-harness-team',
            conversation_id: 'conv-team',
            messages: opts.threadMessages ?? [],
          }),
        } as Response
      }
      if (url.includes('team_rosters') || url.includes('team-rosters')) {
        return {
          ok: true,
          status: 200,
          json: async () => opts.roster ?? HARNESS_ROSTER,
        } as Response
      }
      if (url.includes('/v1/remotes')) {
        return {
          ok: true,
          status: 200,
          json: async () => opts.remotes ?? HERMES_REMOTES,
        } as Response
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ data: [] }),
      } as Response
    }),
  )
}

describe('ChatPage REQ-84 teammate task card', () => {
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

  async function openOn(entry: string, fetchOpts: Parameters<typeof mockFetch>[0] = {}) {
    mockFetch(fetchOpts)
    renderChat(entry)
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })
    return MockWebSocket.instances[0]!
  }

  it('team + stub Hermes tasked session: Open in Hermes uses the stub URL', async () => {
    const ws = await openOn('/chat?team=harness-team')
    await act(async () => {
      ws.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'teammate_task',
            team_id: 'harness-team',
            worker_id: 'hermes',
            worker_kind: 'hermes',
            title: 'list sessions',
            status: 'Done',
          }),
        }),
      )
    })
    const card = await screen.findByTestId('teammate-task-card')
    expect(card).toHaveClass('card')
    expect(screen.getByTestId('teammate-task-title')).toHaveTextContent('list sessions')
    expect(screen.getByText('Done')).toBeInTheDocument()
    const open = await screen.findByRole('link', { name: 'Open in Hermes' })
    expect(open).toHaveAttribute('href', HERMES_UI)
    expect(open).toHaveAttribute('data-testid', 'teammate-task-open')
    expect(card.textContent).not.toMatch(OMB_WORD)
    expect(card.textContent).not.toMatch(/Open in Cursor/i)
  })

  it('OpenMousBot label has no OMB word', async () => {
    const ws = await openOn('/chat?team=harness-team', {
      remotes: {
        object: 'list',
        kinds: [{ id: 'omb', label: 'OpenMousBot' }],
        configured: [
          {
            id: 'omb',
            kind: 'omb',
            label: 'OpenMousBot',
            title: 'OpenMousBot',
            base_url: 'http://127.0.0.1:8802',
            source: 'config',
          },
        ],
      },
    })
    await act(async () => {
      ws.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'teammate_task',
            team_id: 'harness-team',
            worker_id: 'omb',
            worker_kind: 'omb',
            title: 'ping bot',
            status: 'Running',
          }),
        }),
      )
    })
    const open = await screen.findByTestId('teammate-task-open')
    expect(open).toHaveTextContent('Open in OpenMousBot')
    expect(open.textContent).not.toMatch(OMB_WORD)
    expect(document.body.textContent).not.toMatch(OMB_WORD)
  })

  it('no remote on the team: no Open-in button', async () => {
    const ws = await openOn('/chat?team=local-team', { roster: LOCAL_ROSTER })
    await act(async () => {
      ws.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'teammate_task',
            team_id: 'local-team',
            worker_id: 'codey',
            title: 'local only',
            status: 'Running',
          }),
        }),
      )
    })
    expect(await screen.findByTestId('teammate-task-card')).toBeInTheDocument()
    expect(screen.queryByTestId('teammate-task-open')).not.toBeInTheDocument()
    expect(screen.getByTestId('teammate-task-card').textContent).not.toMatch(/Open in /)
  })

  it('solo local API agent does not grow an Open-in-Hermes button', async () => {
    const ws = await openOn('/chat?blueprint=codey')
    await act(async () => {
      ws.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'teammate_task',
            team_id: 'harness-team',
            worker_id: 'hermes',
            title: 'should not open',
            status: 'Running',
          }),
        }),
      )
    })
    expect(await screen.findByTestId('teammate-task-card')).toBeInTheDocument()
    expect(screen.queryByTestId('teammate-task-open')).not.toBeInTheDocument()
  })

  it('disabled when remotes config is empty', async () => {
    const ws = await openOn('/chat?team=harness-team', { remotes: EMPTY_REMOTES })
    await act(async () => {
      ws.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'teammate_task',
            team_id: 'harness-team',
            worker_id: 'hermes',
            title: 'no url',
            status: 'Running',
          }),
        }),
      )
    })
    const open = await screen.findByTestId('teammate-task-open')
    expect(open).toBeDisabled()
    expect(open).toHaveTextContent('Open in Hermes')
    expect(open).toHaveAttribute('aria-label', 'No UI URL configured for Hermes')
  })

  it('PR-opened cards stay View PR and never say Open in {harness}', async () => {
    const ws = await openOn('/chat?team=harness-team')
    await act(async () => {
      ws.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'pr_opened',
            url: GH,
            number: 416,
            title: 'REQ-71',
            opener: { agent_id: 'codey', name: 'Codey' },
          }),
        }),
      )
    })
    const card = await screen.findByTestId('pr-opened-card')
    expect(screen.getByTestId('pr-opened-view')).toHaveTextContent('View PR')
    expect(card.textContent).not.toMatch(/Open in Cursor/i)
    expect(card.textContent).not.toMatch(/Open in Hermes/i)
    expect(card.textContent).not.toMatch(/Open in OpenMousBot/i)
    expect(screen.queryByTestId('teammate-task-card')).not.toBeInTheDocument()
  })
})
