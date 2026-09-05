import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ToastProvider } from '../../components/DaisyUI'
import ChatPage from '../ChatPage'
import * as agentEditorModule from '../../lib/agentSettings'

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

describe('REQ-214: Navbar agent identity hover card', () => {
  beforeEach(() => {
    localStorage.clear()
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

  it('renders hover card wrapping avatar, name, and pencil; whole card is clickable', async () => {
    const openEditorSpy = vi.spyOn(agentEditorModule, 'openAgentEditor')

    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <MemoryRouter initialEntries={['/chat?blueprint=support']}>
            <ChatPage />
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>,
    )

    await act(async () => {
      MockWebSocket.instances[0]?.open()
    })

    const card = screen.getByTestId('selected-agent-header')
    expect(card).toHaveClass('os-navbar-identity-card')
    expect(card).toHaveClass('border-transparent')
    expect(card).toHaveClass('hover:bg-base-200/50')
    expect(card).toHaveClass('hover:border-base-content/10')

    // Avatar, name, and pencil are inside the card
    const avatar = card.querySelector('.os-chat-header__avatar')
    expect(avatar).toBeInTheDocument()
    expect(card).toHaveTextContent('Support')
    const pencil = card.querySelector('.os-navbar-edit-btn')
    expect(pencil).toBeInTheDocument()

    // Clicking anywhere on the card (including clicking the avatar) opens editor
    fireEvent.click(avatar!)
    expect(openEditorSpy).toHaveBeenCalledWith(
      expect.objectContaining({ agentId: 'support' })
    )

    openEditorSpy.mockClear()
    fireEvent.click(card)
    expect(openEditorSpy).toHaveBeenCalledWith(
      expect.objectContaining({ agentId: 'support' })
    )

    openEditorSpy.mockRestore()
  })
})
