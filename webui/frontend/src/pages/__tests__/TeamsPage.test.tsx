import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import TeamsPage from '../TeamsPage'

describe('TeamsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders teams list and allows deletion via ConfirmModal', async () => {
    // Mock successful fetch
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        'test-team': { id: 't1', description: 'desc', llm_profile: 'default' }
      })
    })

    render(<TeamsPage />)

    // Wait for the team to render
    await waitFor(() => {
      expect(screen.getByText('t1')).toBeInTheDocument()
    })

    // Find the delete button.
    // We can't rely on role because it's an icon button, so we use the title or a more specific selector in real scenarios.
    // Here we'll grab the second button in the group (Edit is first, Trash2 is second)
    const deleteBtns = screen.getAllByRole('button').filter(b => b.className.includes('btn-xs') && !b.getAttribute('title'))
    const deleteBtn = deleteBtns[0]

    fireEvent.click(deleteBtn!)

    // Check that ConfirmModal is open
    expect(screen.getByText('Confirm Deletion')).toBeInTheDocument()

    // Mock the deletion POST request
    const postMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200
    })
    global.fetch = postMock

    // Click Confirm on the modal
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    // Verify POST was made
    expect(postMock).toHaveBeenCalled()
  })
})
