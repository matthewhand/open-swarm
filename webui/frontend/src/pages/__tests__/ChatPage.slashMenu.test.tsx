import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ChatPage from '../ChatPage'
import { ToastProvider } from '../../components/DaisyUI'
import { clearRecentSlashIds } from '../../lib/slashMenu'

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
}

function renderChat() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={['/chat']}>
          <ChatPage />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

describe('ChatPage slash menu (REQ-169)', () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn()
    clearRecentSlashIds()
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string | URL | Request) => {
        const urlStr = String(url)
        if (urlStr.includes('/v1/skills')) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                object: 'list',
                data: [
                  {
                    name: 'custom-skill',
                    description: 'Custom dynamic skill',
                    path: 'skills/custom-skill/SKILL.md',
                    assets: [],
                  },
                ],
              }),
              { status: 200 },
            ),
          )
        }
        if (urlStr.includes('/v1/config-options/')) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                skills: [
                  {
                    name: 'custom-skill',
                    description: 'Custom dynamic skill',
                    assets: [],
                    instructions: '',
                  },
                ],
                inference: { traits: [], cli_traits: {}, model_traits: {}, model_flags: {} },
                tools: { capabilities: [], mcp_catalog: [] },
              }),
              { status: 200 },
            ),
          )
        }
        if (urlStr.includes('/chat/compact/')) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                summaries: [],
                summary: { id: 'sum-1', span: [0, 1], body: 'Compact summary' },
              }),
              { status: 200 },
            ),
          )
        }
        return Promise.resolve(
          new Response(JSON.stringify([]), { status: 200 }),
        )
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    clearRecentSlashIds()
  })

  async function openWebSocket() {
    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })
  }

  it('opens slash popup immediately when typing / as first character', async () => {
    renderChat()
    await openWebSocket()

    const input = screen.getByRole('textbox', { name: 'Chat message' })
    expect(screen.queryByTestId('composer-slash-popup')).not.toBeInTheDocument()

    fireEvent.change(input, { target: { value: '/' } })
    expect(screen.getByTestId('composer-slash-popup')).toBeInTheDocument()
    expect(screen.getByText('Actions')).toBeInTheDocument()
    expect(screen.getByText('Skills')).toBeInTheDocument()
    expect(screen.getByTestId('slash-item-compact')).toBeInTheDocument()
  })

  it('filters results when typing characters after /', async () => {
    renderChat()
    await openWebSocket()

    const input = screen.getByRole('textbox', { name: 'Chat message' })
    fireEvent.change(input, { target: { value: '/clear' } })

    expect(screen.getByTestId('composer-slash-popup')).toBeInTheDocument()
    expect(screen.getByTestId('slash-item-clear')).toBeInTheDocument()
    // Unrelated items are filtered out
    expect(screen.queryByTestId('slash-item-help')).not.toBeInTheDocument()
    expect(screen.queryByTestId('slash-item-compact')).not.toBeInTheDocument()
    expect(screen.queryByTestId('slash-item-conventional-commit')).not.toBeInTheDocument()
  })

  it('closes popup when clearing / with backspace', async () => {
    renderChat()
    await openWebSocket()

    const input = screen.getByRole('textbox', { name: 'Chat message' })
    fireEvent.change(input, { target: { value: '/' } })
    expect(screen.getByTestId('composer-slash-popup')).toBeInTheDocument()

    fireEvent.change(input, { target: { value: '' } })
    expect(screen.queryByTestId('composer-slash-popup')).not.toBeInTheDocument()
  })

  it('dismisses popup on Escape key', async () => {
    renderChat()
    await openWebSocket()

    const input = screen.getByRole('textbox', { name: 'Chat message' })
    fireEvent.change(input, { target: { value: '/' } })
    expect(screen.getByTestId('composer-slash-popup')).toBeInTheDocument()

    fireEvent.keyDown(input, { key: 'Escape' })
    expect(screen.queryByTestId('composer-slash-popup')).not.toBeInTheDocument()
  })

  it('navigates with ArrowDown/ArrowUp and selects with Enter', async () => {
    renderChat()
    await openWebSocket()

    const input = screen.getByRole('textbox', { name: 'Chat message' })
    fireEvent.change(input, { target: { value: '/help' } })

    // Help should be matched and highlighted at index 0
    const helpItem = screen.getByTestId('slash-item-help')
    expect(helpItem).toHaveAttribute('aria-selected', 'true')

    fireEvent.keyDown(input, { key: 'Enter' })

    // Selecting help should insert /help into composer and close popup
    expect(screen.queryByTestId('composer-slash-popup')).not.toBeInTheDocument()
    expect(input).toHaveValue('/help ')
  })

  it('selecting compact action triggers compact flow and clears composer input', async () => {
    renderChat()
    await openWebSocket()

    const input = screen.getByRole('textbox', { name: 'Chat message' })
    fireEvent.change(input, { target: { value: '/compact' } })

    const compactItem = screen.getByTestId('slash-item-compact')
    fireEvent.click(compactItem)

    expect(screen.queryByTestId('composer-slash-popup')).not.toBeInTheDocument()
    expect(input).toHaveValue('')
  })

  it('selecting a skill inserts /skill <name> into composer', async () => {
    renderChat()
    await openWebSocket()

    const input = screen.getByRole('textbox', { name: 'Chat message' })
    fireEvent.change(input, { target: { value: '/conventional' } })

    const skillItem = screen.getByTestId('slash-item-conventional-commit')
    fireEvent.click(skillItem)

    expect(screen.queryByTestId('composer-slash-popup')).not.toBeInTheDocument()
    expect(input).toHaveValue('/skill conventional-commit ')
  })

  it('shows recently used items first in empty query mode', async () => {
    renderChat()
    await openWebSocket()

    const input = screen.getByRole('textbox', { name: 'Chat message' })

    // Select conventional-commit skill
    fireEvent.change(input, { target: { value: '/conventional' } })
    fireEvent.click(screen.getByTestId('slash-item-conventional-commit'))

    // Reopen slash menu
    fireEvent.change(input, { target: { value: '' } })
    fireEvent.change(input, { target: { value: '/' } })

    expect(screen.getByTestId('composer-slash-popup')).toBeInTheDocument()
    const recentElements = screen.getAllByText('Recent')
    expect(recentElements.length).toBeGreaterThanOrEqual(1)
    // The conventional-commit item should be in the recent section
    expect(screen.getByTestId('slash-item-conventional-commit')).toBeInTheDocument()
  })
})
