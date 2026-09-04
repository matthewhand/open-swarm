import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import AgentSidebar from '../AgentSidebar'

describe('AgentSidebar Rail Scroll Fade (REQ-99)', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
  })

  it('renders fade element above plugins footer with pointer-events-none', () => {
    const blueprints = [
      {
        id: 'support_agent',
        object: 'blueprint' as const,
        name: 'Support Agent',
        description: 'Customer help',
        role: 'support',
        installed: true,
        compiled: true,
      },
      {
        id: 'codey',
        object: 'blueprint' as const,
        name: 'Codey',
        description: 'Code assistant',
        role: 'default',
        installed: true,
        compiled: true,
      },
    ]

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AgentSidebar blueprints={blueprints} />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    const fade = screen.getByTestId('rail-scroll-fade')
    expect(fade).toBeInTheDocument()
    expect(fade).toHaveClass('os-rail-scroll-fade')
    expect(fade).toHaveClass('pointer-events-none')

    // Plugins button is clickable and opens modal
    const pluginsBtn = screen.getByRole('button', { name: 'Plugins' })
    expect(pluginsBtn).toBeInTheDocument()
    fireEvent.click(pluginsBtn)
    expect(screen.getByRole('dialog', { name: 'Plugins' })).toBeInTheDocument()
  })

  it('activates fade opacity when scrollable list can scroll', () => {
    const blueprints = [
      {
        id: 'support_agent',
        object: 'blueprint' as const,
        name: 'Support Agent',
        description: 'Customer help',
        role: 'support',
        installed: true,
        compiled: true,
      },
    ]

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AgentSidebar blueprints={blueprints} />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    const nav = screen.getByRole('navigation', { name: 'Agent list' })
    const fade = screen.getByTestId('rail-scroll-fade')

    // Simulate overflow
    Object.defineProperty(nav, 'scrollHeight', { value: 600, configurable: true })
    Object.defineProperty(nav, 'clientHeight', { value: 200, configurable: true })
    fireEvent.scroll(nav)

    expect(fade).toHaveAttribute('data-can-scroll', 'true')
    expect(fade).toHaveClass('opacity-100')

    // Simulate short list
    Object.defineProperty(nav, 'scrollHeight', { value: 150, configurable: true })
    Object.defineProperty(nav, 'clientHeight', { value: 200, configurable: true })
    fireEvent.scroll(nav)

    expect(fade).toHaveAttribute('data-can-scroll', 'false')
    expect(fade).toHaveClass('opacity-0')
  })
})
