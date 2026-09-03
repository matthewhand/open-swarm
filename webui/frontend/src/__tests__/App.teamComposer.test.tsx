import { fireEvent, render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'

function renderApp() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  )
}

describe('SPA + team composer entry', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: [] }),
      } as Response),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('opens the overlay from + without adding a top-nav Teams tab', async () => {
    renderApp()

    const primary = screen.getByRole('navigation', { name: 'Primary' })
    expect(within(primary).getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/')
    expect(within(primary).getByRole('link', { name: 'Chat' })).toHaveAttribute('href', '/chat')
    const spaTeamsTab = within(primary)
      .queryAllByRole('link')
      .find((el) => el.textContent?.trim() === 'Teams' && el.getAttribute('href') === '/teams')
    expect(spaTeamsTab).toBeUndefined()

    fireEvent.click(screen.getByRole('button', { name: /compose team/i }))
    expect(await screen.findByRole('heading', { name: /new team/i })).toBeInTheDocument()
    expect(screen.getByTestId('team-drop-zone')).toHaveTextContent(/drop agents here/i)
  })
})
