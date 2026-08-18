import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TeamsPage from '../TeamsPage'

describe('TeamsPage honesty', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows an empty error state instead of demo teams when export fails', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('network down'))

    render(
      <MemoryRouter>
        <TeamsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/Could not load teams/)
    })
    expect(screen.getByText('Teams unavailable')).toBeInTheDocument()
    expect(screen.queryByText('Code Review Team')).not.toBeInTheDocument()
    expect(screen.queryByText('Documentation Squad')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open Django launcher/i })).toHaveAttribute(
      'href',
      '/teams/launch/',
    )
  })
})
