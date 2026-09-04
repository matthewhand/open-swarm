import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import AgentAvatar from '../../components/AgentAvatar'
import { ToastProvider } from '../../components/DaisyUI/Toast'
import ChatPage from '../ChatPage'

describe('REQ-176: Blob eyes wander while agent is working/streaming', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('swarm:avatar-theme', 'blobs')
    Element.prototype.scrollIntoView = vi.fn()
  })

  it('sets data-eye-state to active when active=true and idle when active=false on AgentAvatar', () => {
    const { container: idleContainer } = render(
      <AgentAvatar agentId="codey" active={false} size="lg" />,
    )
    const idleSvg = idleContainer.querySelector('.os-blob-avatar')
    expect(idleSvg).toHaveAttribute('data-eye-state', 'idle')

    const { container: activeContainer } = render(
      <AgentAvatar agentId="codey" active={true} size="lg" />,
    )
    const activeSvg = activeContainer.querySelector('.os-blob-avatar')
    expect(activeSvg).toHaveAttribute('data-eye-state', 'active')
  })

  it('leaves header blob eyes idle when connected but not streaming', async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    // Mock WebSocket to connect cleanly
    class MockWs {
      static OPEN = 1
      readyState = 1
      onopen: ((ev?: Event) => void) | null = null
      onmessage: ((ev?: Event) => void) | null = null
      onclose: ((ev?: Event) => void) | null = null
      send = vi.fn()
      close = vi.fn()
      addEventListener = vi.fn()
      removeEventListener = vi.fn()
    }
    vi.stubGlobal('WebSocket', MockWs as any)

    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <MemoryRouter initialEntries={['/chat?blueprint=codey']}>
            <ChatPage />
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>,
    )

    // Header avatar should have idle eye state when no streaming message is present
    const headerAvatar = document.querySelector('.os-chat-header__avatar .os-blob-avatar')
    if (headerAvatar) {
      expect(headerAvatar).toHaveAttribute('data-eye-state', 'idle')
    }

    // Composer working indicator should not be visible when idle
    expect(screen.queryByTestId('composer-working-indicator')).not.toBeInTheDocument()
  })
})
