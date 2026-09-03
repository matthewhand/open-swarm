import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import SearchPalette, { SEARCH_PALETTE_TABS } from '../SearchPalette'

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
]

function renderPalette(open = true, onClose = vi.fn()) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return {
    onClose,
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <SearchPalette open={open} onClose={onClose} />
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  }
}

describe('SearchPalette', () => {
  beforeEach(() => {
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
  })

  it('opens as an overlay with Search placeholder, tab row, and keyboard focus', async () => {
    const { onClose } = renderPalette()

    const dialog = screen.getByRole('dialog', { name: 'Search' })
    expect(dialog).toBeInTheDocument()
    const input = screen.getByRole('combobox', { name: 'Search' })
    expect(input).toHaveAttribute('placeholder', 'Search')

    for (const tab of SEARCH_PALETTE_TABS) {
      expect(screen.getByRole('tab', { name: tab })).toBeInTheDocument()
    }
    expect(screen.getByRole('tab', { name: 'All' })).toHaveAttribute('aria-selected', 'true')

    const first = await screen.findByRole('option', { name: /Support/i })
    expect(first).toHaveAttribute('aria-selected', 'true')
    expect(first.textContent).toMatch(/⌃1/)

    fireEvent.keyDown(window, { key: 'ArrowDown' })
    await waitFor(() => {
      expect(screen.getAllByRole('option')[1]).toHaveAttribute('aria-selected', 'true')
    })

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })

  it('shows an empty state on tabs without rows', () => {
    renderPalette()
    fireEvent.click(screen.getByRole('tab', { name: 'Messages' }))
    expect(screen.getByText('No results')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Messages' })).toHaveAttribute('aria-selected', 'true')
  })
})
