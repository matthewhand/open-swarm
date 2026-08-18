import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import BlueprintsPage from '../BlueprintsPage'

describe('BlueprintsPage honesty', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows an empty error state instead of demo rows when /v1/blueprints fails', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({}),
    } as Response)

    render(
      <MemoryRouter>
        <BlueprintsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/Could not load blueprints/)
    })
    expect(screen.getByText('Blueprints unavailable')).toBeInTheDocument()
    expect(screen.queryByText('Codey')).not.toBeInTheDocument()
    expect(screen.queryByText('Chatbot')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open Django library/i })).toHaveAttribute(
      'href',
      '/blueprint-library/',
    )
  })

  it('links Launch to SPA chat with the blueprint preselected', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        data: [{ id: 'codey', name: 'Codey', description: 'Code assistant' }],
      }),
    } as Response)

    render(
      <MemoryRouter>
        <BlueprintsPage />
      </MemoryRouter>,
    )

    const launch = await screen.findByRole('link', { name: /Open chat with Codey/i })
    expect(launch).toHaveAttribute('href', '/chat?blueprint=codey')
  })
})
