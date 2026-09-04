import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AgentPinGrid from '../AgentPinGrid'
import AgentSidebar from '../AgentSidebar'
import { PINNED_AGENTS_STORAGE_KEY } from '../../lib/pinnedAgents'
import { endAgentDrag } from '../../lib/pinnedAgents'

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

function mockDataTransfer() {
  const store: Record<string, string> = {}
  const types: string[] = []
  return {
    dropEffect: 'none',
    effectAllowed: 'all',
    types,
    setData(type: string, value: string) {
      store[type] = value
      if (!types.includes(type)) types.push(type)
    },
    getData(type: string) {
      return store[type] ?? ''
    },
    clearData() {
      Object.keys(store).forEach((key) => delete store[key])
      types.length = 0
    },
  }
}

function renderChrome(initialEntry = '/') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <AgentPinGrid />
        <AgentSidebar open onClose={() => undefined} />
        <Routes>
          <Route path="/" element={<p>Home</p>} />
          <Route path="/chat" element={<p>Chat for tests</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AgentPinGrid drag-to-pin', () => {
  beforeEach(() => {
    localStorage.clear()
    endAgentDrag()
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
    endAgentDrag()
    localStorage.clear()
  })

  it('has an unlabeled drop grid (no Favourites heading) that accepts a sidepane row', async () => {
    renderChrome()

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = (await within(list).findAllByRole('link', { name: /Codey/ })).find((el) =>
      (el.getAttribute('href') || '').includes('blueprint=codey'),
    )
    if (!codey) throw new Error('missing Codey rail row')
    expect(codey).toHaveAttribute('draggable', 'true')

    expect(screen.queryByText(/Favourites/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /Favourites/i })).not.toBeInTheDocument()

    const grid = screen.getByTestId('agent-pin-grid')
    const dt = mockDataTransfer()
    fireEvent.dragStart(codey, { dataTransfer: dt })
    fireEvent.dragOver(grid, { dataTransfer: dt })
    fireEvent.drop(grid, { dataTransfer: dt })
    fireEvent.dragEnd(codey, { dataTransfer: dt })

    const tile = await within(grid).findByRole('link', { name: /Codey/ })
    expect(tile).toHaveAttribute('href', '/chat?blueprint=codey')
    expect(
      within(list)
        .getAllByRole('link', { name: /Codey/ })
        .some((el) => (el.getAttribute('href') || '').includes('blueprint=codey')),
    ).toBe(true)
    expect(JSON.parse(localStorage.getItem(PINNED_AGENTS_STORAGE_KEY) || '[]')).toEqual([
      { id: 'codey', name: 'Codey' },
    ])
  })

  it('restores tiles from localStorage and lets the user remove one', async () => {
    localStorage.setItem(
      PINNED_AGENTS_STORAGE_KEY,
      JSON.stringify([{ id: 'stewie', name: 'Stewie' }]),
    )
    renderChrome('/chat?blueprint=stewie')

    const grid = screen.getByTestId('agent-pin-grid')
    const tile = await within(grid).findByRole('link', { name: /Stewie/ })
    expect(tile).toHaveAttribute('aria-current', 'page')

    fireEvent.click(screen.getByRole('button', { name: /Remove Stewie/i }))
    await waitFor(() => {
      expect(within(grid).queryByRole('link', { name: /Stewie/ })).not.toBeInTheDocument()
    })
    expect(JSON.parse(localStorage.getItem(PINNED_AGENTS_STORAGE_KEY) || '[]')).toEqual([])
    expect(screen.getByRole('navigation', { name: 'Agent list' })).toBeInTheDocument()
  })
})
