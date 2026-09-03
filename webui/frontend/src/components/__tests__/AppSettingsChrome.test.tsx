import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../../App'

function renderApp() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ data: [] }),
    } as Response),
  )
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  )
}

describe('SPA settings chrome (REQ-19)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('opens a modal-end sheet from the gear and keeps Settings out of nav/dock', () => {
    renderApp()

    const primary = screen.getByRole('navigation', { name: 'Primary' })
    expect(primary.querySelector('a[href="/settings/"]')).toBeNull()
    expect(primary.textContent).not.toMatch(/\bSettings\b/)

    const dock = screen.getByRole('navigation', { name: 'Mobile primary' })
    expect(dock.querySelector('a[href="/settings/"]')).toBeNull()
    expect(dock.textContent).not.toMatch(/\bSettings\b/)

    fireEvent.click(screen.getByRole('button', { name: 'Open settings' }))
    const dialog = screen.getByRole('dialog', { hidden: true })
    expect(dialog).toHaveClass('modal-end')
    expect(dialog).toHaveClass('modal-open')
    expect(screen.getByRole('navigation', { name: 'Settings sections' })).toBeInTheDocument()
  })
})
