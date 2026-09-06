import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SearchPalette, { OPEN_SEARCH_EVENT, openSearchPalette } from '../SearchPalette'
import { HIDDEN_AGENTS_STORAGE_KEY } from '../../lib/hiddenAgents'

function renderPalette(options?: { filterHidden?: boolean; tab?: any; query?: string }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const onClose = vi.fn()
  const res = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SearchPalette open={true} onClose={onClose} options={options} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return { ...res, onClose }
}

describe('REQ-190: Hidden Bots opens Search palette filtered to hidden', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/v1/blueprints')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              data: [
                { id: 'gate', name: 'Gate Agent', description: 'Safety gate', role: 'gate', rail: true },
                { id: 'skeptic', name: 'Skeptic Agent', description: 'Reviewer', role: 'skeptic', rail: true },
                { id: 'codey', name: 'Codey', description: 'Developer agent', rail: true },
              ],
            }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ data: [] }),
        } as Response
      }),
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('openSearchPalette dispatches OPEN_SEARCH_EVENT with options', () => {
    const spy = vi.fn()
    window.addEventListener(OPEN_SEARCH_EVENT, spy)
    openSearchPalette({ filterHidden: true })
    expect(spy).toHaveBeenCalled()
    const event = spy.mock.calls[0][0] as CustomEvent
    expect(event.detail).toEqual({ filterHidden: true })
    window.removeEventListener(OPEN_SEARCH_EVENT, spy)
  })

  it('displays Hidden only filter indicator and shows only hidden bots when filterHidden is true', async () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(['gate', 'skeptic']))
    renderPalette({ filterHidden: true })

    const indicator = await screen.findByTestId('hidden-filter-indicator')
    expect(indicator).toBeInTheDocument()
    expect(indicator).toHaveTextContent('Hidden only')

    // Gate and Skeptic should be shown
    expect(await screen.findByText('Gate Agent')).toBeInTheDocument()
    expect(screen.getByText('Skeptic Agent')).toBeInTheDocument()

    // Codey (not hidden) should NOT be shown
    expect(screen.queryByText('Codey')).not.toBeInTheDocument()
  })

  it('allows filtering within hidden bots via search input', async () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(['gate', 'skeptic']))
    renderPalette({ filterHidden: true })

    await screen.findByText('Gate Agent')
    const input = screen.getByRole('combobox', { name: 'Search' })
    fireEvent.change(input, { target: { value: 'skep' } })

    expect(screen.getByText('Skeptic Agent')).toBeInTheDocument()
    expect(screen.queryByText('Gate Agent')).not.toBeInTheDocument()
  })

  it('displays Unhide button on hidden bot rows and clicking it unhides the agent', async () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(['gate', 'skeptic']))
    renderPalette({ filterHidden: true })

    await screen.findByText('Gate Agent')
    const unhideGateBtn = screen.getByTestId('unhide-gate')
    expect(unhideGateBtn).toBeInTheDocument()

    fireEvent.click(unhideGateBtn)

    // Gate should now be removed from hidden list in localStorage
    const remaining = JSON.parse(localStorage.getItem(HIDDEN_AGENTS_STORAGE_KEY) || '[]')
    expect(remaining).not.toContain('gate')
    expect(remaining).toContain('skeptic')

    // Gate should disappear from the filtered list
    expect(screen.queryByText('Gate Agent')).not.toBeInTheDocument()
    expect(screen.getByText('Skeptic Agent')).toBeInTheDocument()
  })

  it('displays honest empty state when hidden set is empty', async () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify([]))
    renderPalette({ filterHidden: true })

    const empty = await screen.findByTestId('search-empty-hidden')
    expect(empty).toBeInTheDocument()
    expect(empty).toHaveTextContent('No hidden agents found')
  })

  it('clears hidden filter when clicking the × button on filter indicator', async () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(['gate']))
    renderPalette({ filterHidden: true })

    const indicator = await screen.findByTestId('hidden-filter-indicator')
    const clearBtn = within(indicator).getByRole('button', { name: /Clear hidden filter/i })
    fireEvent.click(clearBtn)

    // Filter indicator should disappear
    expect(screen.queryByTestId('hidden-filter-indicator')).not.toBeInTheDocument()
  })
})
