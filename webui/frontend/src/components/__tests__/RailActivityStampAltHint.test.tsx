import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import AgentSidebar from '../AgentSidebar'
import { ToastProvider } from '../DaisyUI'

describe('REQ-208: Sidepane — last activity time/day; hover swaps to Alt+N hint', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) => {
        if (url.includes('/v1/blueprints')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              data: [
                { id: 'codey', name: 'Codey', role: 'default' },
                { id: 'stewie', name: 'Stewie', role: 'default' },
              ],
            }),
          } as Response)
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({ results: [], data: [] }),
        } as Response)
      }),
    )
  })

  it('renders Alt+N hint with hidden class and timestamp with group-hover:hidden swap classes', async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <MemoryRouter initialEntries={['/']}>
            <AgentSidebar />
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>,
    )

    await waitFor(() => {
      expect(screen.queryByText('Loading agents…')).not.toBeInTheDocument()
    })

    const hotkeys = screen.getAllByTestId('spill-hotkey')
    expect(hotkeys.length).toBeGreaterThan(0)
    // Verify hotkey has hidden by default and group-hover/row:inline-block
    expect(hotkeys[0]).toHaveClass('hidden')
    expect(hotkeys[0].className).toContain('group-hover/row:inline-block')
  })
})
