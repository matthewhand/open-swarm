import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import SearchPalette, { SEARCH_PALETTE_TABS } from '../SearchPalette'
import { THEME_TOGGLE_EVENT } from '../../lib/theme'

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
    expect(dialog).toHaveClass('os-search-palette--centered')
    expect(dialog).toHaveClass('os-search-palette--large')
    const overlay = screen.getByTestId('os-search-overlay')
    expect(overlay).toHaveClass('os-search-overlay--centered')
    const input = screen.getByRole('combobox', { name: 'Search' })
    expect(input).toHaveAttribute('placeholder', 'Search')
    expect(document.querySelector('.os-search-palette__kbd')).toBeTruthy()
    fireEvent.change(input, { target: { value: 'codey' } })
    expect(document.querySelector('.os-search-palette__kbd')).toBeNull()
    fireEvent.change(input, { target: { value: '' } })
    expect(document.querySelector('.os-search-palette__kbd')).toBeTruthy()

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

  it('Bots tab lists Support + catalog agents and Enter chooses a /chat href (REQ-17 / #322)', async () => {
    const { onClose } = renderPalette()
    expect(await screen.findByRole('option', { name: /Codey/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Bots' }))
    expect(screen.getByRole('tab', { name: 'Bots' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('option', { name: /Support/ })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Codey/ })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /Toggle theme/ })).not.toBeInTheDocument()

    fireEvent.keyDown(window, { key: 'Enter' })
    expect(onClose).toHaveBeenCalled()
  })

  it('Actions tab lists theme + Django operator destinations, not live remotes (REQ-17 / #322)', () => {
    const toggled: string[] = []
    const onToggle = () => toggled.push('theme')
    window.addEventListener('swarm:toggle-theme', onToggle)
    const { onClose } = renderPalette()
    fireEvent.click(screen.getByRole('tab', { name: 'Actions' }))
    expect(screen.getByRole('option', { name: /Toggle theme/ })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Blueprints/ })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Teams/ })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Settings/ })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Show LLM profiles/ })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /Hermes/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /Rakazo/ })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('option', { name: /Toggle theme/ }))
    expect(onClose).toHaveBeenCalled()
    expect(toggled).toEqual(['theme'])
    window.removeEventListener('swarm:toggle-theme', onToggle)
  })

  it('filters All-tab rows by query without hiding the overlay chrome', async () => {
    renderPalette()
    const input = screen.getByRole('combobox', { name: 'Search' })
    fireEvent.change(input, { target: { value: 'codey' } })
    expect(await screen.findByRole('option', { name: /Codey/ })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /Support/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /Toggle theme/ })).not.toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'All' })).toBeInTheDocument()
  })
})

function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="palette-loc">{`${loc.pathname}${loc.search}`}</div>
}

function renderRoutedPalette() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const onClose = vi.fn()
  return {
    onClose,
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/']}>
          <SearchPalette open onClose={onClose} />
          <LocationProbe />
          <Routes>
            <Route path="/" element={<div>home</div>} />
            <Route path="/chat" element={<div>chat</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  }
}

describe('SearchPalette choose + actions (REQ-5c #322)', () => {
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
    vi.restoreAllMocks()
  })

  it('navigates a bot row to /chat?blueprint= and closes the overlay', async () => {
    const { onClose } = renderRoutedPalette()
    const codey = await screen.findByRole('option', { name: /Codey/i })
    fireEvent.click(codey)
    expect(onClose).toHaveBeenCalled()
    expect(screen.getByTestId('palette-loc')).toHaveTextContent('/chat?blueprint=codey')
  })

  it('chooses the first visible row with Ctrl+1', async () => {
    const { onClose } = renderRoutedPalette()
    await screen.findByRole('option', { name: /Support/i })
    fireEvent.keyDown(window, { key: '1', ctrlKey: true })
    expect(onClose).toHaveBeenCalled()
    expect(screen.getByTestId('palette-loc')).toHaveTextContent('/chat?blueprint=support')
  })

  it('filters bots by query and Enter chooses the highlighted row', async () => {
    const { onClose } = renderRoutedPalette()
    await screen.findByRole('option', { name: /Codey/i })
    fireEvent.change(screen.getByRole('combobox', { name: 'Search' }), {
      target: { value: 'codey' },
    })
    await waitFor(() => {
      expect(screen.queryByRole('option', { name: /Support/i })).not.toBeInTheDocument()
    })
    expect(screen.getByRole('option', { name: /Codey/i })).toHaveAttribute('aria-selected', 'true')
    fireEvent.keyDown(window, { key: 'Enter' })
    expect(onClose).toHaveBeenCalled()
    expect(screen.getByTestId('palette-loc')).toHaveTextContent('/chat?blueprint=codey')
  })

  it('Actions → Toggle theme dispatches swarm:toggle-theme without leaving chat', async () => {
    const toggled = vi.fn()
    window.addEventListener(THEME_TOGGLE_EVENT, toggled)
    const { onClose } = renderRoutedPalette()
    fireEvent.click(screen.getByRole('tab', { name: 'Actions' }))
    fireEvent.click(await screen.findByRole('option', { name: /Toggle theme/i }))
    expect(onClose).toHaveBeenCalled()
    expect(toggled).toHaveBeenCalled()
    expect(screen.getByTestId('palette-loc')).toHaveTextContent('/')
    window.removeEventListener(THEME_TOGGLE_EVENT, toggled)
  })

  it('Actions → Show LLM profiles opens Settings on the profiles pane', async () => {
    const opened: Array<{ section?: string }> = []
    const onOpen = (event: Event) => {
      opened.push((event as CustomEvent<{ section?: string }>).detail ?? {})
    }
    window.addEventListener('swarm:open-settings', onOpen)
    const { onClose } = renderRoutedPalette()
    fireEvent.click(screen.getByRole('tab', { name: 'Actions' }))
    fireEvent.click(await screen.findByRole('option', { name: /Show LLM profiles/i }))
    window.removeEventListener('swarm:open-settings', onOpen)
    expect(onClose).toHaveBeenCalled()
    expect(opened).toEqual([{ section: 'llm-profiles' }])
    expect(screen.getByTestId('palette-loc')).toHaveTextContent('/')
  })

  it('Actions Blueprints stays on chat (overlay, not a Django eject)', async () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { ...window.location, assign })
    const { onClose } = renderRoutedPalette()
    fireEvent.click(screen.getByRole('tab', { name: 'Actions' }))
    fireEvent.click(await screen.findByRole('option', { name: /^Blueprints/i }))
    expect(onClose).toHaveBeenCalled()
    expect(assign).not.toHaveBeenCalled()
    expect(screen.getByTestId('palette-loc')).toHaveTextContent('/')
  })
})
