import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import AgentSidebar from '../AgentSidebar'
import { HIDDEN_AGENTS_STORAGE_KEY } from '../../lib/hiddenAgents'

const blueprints = [
  {
    id: 'codey',
    object: 'blueprint' as const,
    name: 'Codey',
    description: 'Code assistant',
    abbreviation: null,
    required_mcp_servers: [],
    tags: [],
    installed: true,
    compiled: true,
  },
  {
    id: 'stewie',
    object: 'blueprint' as const,
    name: 'Stewie',
    description: 'Helpful agent',
    abbreviation: null,
    required_mcp_servers: [],
    tags: [],
    installed: true,
    compiled: true,
  },
]

function renderSidebar(initialEntry = '/chat') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <AgentSidebar open onClose={() => undefined} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function storedHidden(): string[] {
  return JSON.parse(localStorage.getItem(HIDDEN_AGENTS_STORAGE_KEY) || '[]')
}

describe('AgentSidebar hide / unhide', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: blueprints }),
      } as Response),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('lists agents and hides one from the main list via the context menu', async () => {
    renderSidebar()

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    expect(within(list).getByRole('link', { name: /Stewie/ })).toBeInTheDocument()

    fireEvent.contextMenu(codey)
    fireEvent.click(await screen.findByRole('menuitem', { name: /Hide from sidebar/i }))

    await waitFor(() => {
      expect(within(list).queryByRole('link', { name: /Codey/ })).not.toBeInTheDocument()
    })
    expect(within(list).getByRole('link', { name: /Stewie/ })).toBeInTheDocument()
    expect(storedHidden()).toEqual(['codey'])

    fireEvent.click(screen.getByRole('button', { name: /Hidden/i }))
    expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Unhide Codey/i }))
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Hidden/i })).not.toBeInTheDocument()
    })
    expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()
    expect(storedHidden()).toEqual([])
  })

  it('restores hidden agents from localStorage after remount (reload)', async () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(['codey']))
    renderSidebar()

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    await waitFor(() => {
      expect(within(list).queryByRole('link', { name: /Codey/ })).not.toBeInTheDocument()
    })
    expect(within(list).getByRole('link', { name: /Stewie/ })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Hidden/i }))
    expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()
  })
})

describe('AgentSidebar special roles', () => {
  const roster = [
    {
      id: 'codey',
      object: 'blueprint' as const,
      name: 'Codey',
      description: 'Code',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
      role: null,
    },
    {
      id: 'skeptic',
      object: 'blueprint' as const,
      name: 'Skeptic',
      description: 'Retry stub',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
      role: 'skeptic',
    },
    {
      id: 'gate',
      object: 'blueprint' as const,
      name: 'Gate',
      description: 'Approve stub',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
      role: 'gate',
    },
    {
      id: 'support',
      object: 'blueprint' as const,
      name: 'Support',
      description: 'Onboarding. First team.',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
      role: 'support',
    },
  ]

  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: roster }),
      } as Response),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('lists Support first with a role=support look, not a diamond', async () => {
    renderSidebar('/chat?blueprint=support')
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const links = within(list).getAllByRole('link')
    expect(links[0]).toHaveTextContent('Support')
    expect(links[0]).toHaveAttribute('data-role', 'support')
    expect(links[0].querySelector('.os-agent-dot')).toBeNull()
    expect(links[0].querySelector('.os-role-pill--support')).not.toBeNull()
    expect(within(list).getByRole('link', { name: /Gate/ })).toHaveAttribute('data-role', 'gate')
    expect(within(list).getByRole('link', { name: /Skeptic/ })).toHaveAttribute(
      'data-role',
      'skeptic',
    )
  })
})
