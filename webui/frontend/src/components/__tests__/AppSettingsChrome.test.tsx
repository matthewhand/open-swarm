import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../../App'

function renderApp() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  Element.prototype.scrollIntoView = vi.fn()
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

  it('opens a modal-end sheet from the gear and keeps Settings out of Grok chrome', () => {
    renderApp()

    // 322 chrome: left rail + chat, no product top-nav / mobile dock.
    expect(screen.queryByRole('navigation', { name: 'Primary' })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Mobile primary' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /^Settings$/i })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Open settings' }))
    const dialog = screen.getByRole('dialog', { name: 'Settings', hidden: true })
    expect(dialog).toHaveClass('modal-end')
    expect(dialog).toHaveClass('modal-open')
    expect(screen.getByRole('navigation', { name: 'Settings sections' })).toBeInTheDocument()
    // REQ-48: Settings is a sheet over chat, not a route that unmounts the composer.
    expect(screen.getByRole('textbox', { name: 'Chat message' })).toBeInTheDocument()
  })
})
