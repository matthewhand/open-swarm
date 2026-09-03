import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import TeamsSheet from '../TeamsSheet'
import { DEMO_TEAM_ROSTER, OPEN_TEAMS_SHEET_EVENT } from '../../lib/teamRosters'

describe('TeamsSheet', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: [DEMO_TEAM_ROSTER] }),
      } as Response),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('opens from the manage-teams event and lists roster members', async () => {
    render(<TeamsSheet />)
    expect(screen.queryByRole('dialog', { hidden: true, name: /Manage Teams/i })).toBeNull()

    window.dispatchEvent(new CustomEvent(OPEN_TEAMS_SHEET_EVENT))

    const dialog = await screen.findByRole('dialog', { hidden: true, name: /Manage Teams/i })
    expect(dialog).toHaveClass('modal-open')
    await waitFor(() => {
      expect(screen.getByText('Demo Council')).toBeInTheDocument()
    })
    expect(screen.getByText(/Planner/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Django alias admin/i })).toHaveAttribute(
      'href',
      '/teams/',
    )
  })
})
