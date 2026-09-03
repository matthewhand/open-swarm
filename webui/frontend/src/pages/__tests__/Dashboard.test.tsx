import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Dashboard from '../Dashboard'

function renderDashboard() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Dashboard quick-action cards', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ data: [] }),
      } as Response),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the four actions as large cards, not rainbow buttons', () => {
    renderDashboard()

    const launch = screen.getByRole('link', { name: /Launch Team/i })
    const browse = screen.getByRole('link', { name: /Browse Blueprints/i })
    const manage = screen.getByRole('link', { name: /Manage Teams/i })
    const settings = screen.getByRole('link', { name: /Settings/i })

    expect(launch).toHaveAttribute('href', '/teams/launch/')
    expect(browse).toHaveAttribute('href', '/blueprint-library/')
    expect(manage).toHaveAttribute('href', '/teams/')
    expect(settings).toHaveAttribute('href', '/settings/')

    for (const card of [launch, browse, manage, settings]) {
      expect(card).toHaveClass('os-action-card')
      expect(card.className).not.toMatch(/btn-primary|btn-secondary|btn-accent|btn-info/)
    }
  })
})
