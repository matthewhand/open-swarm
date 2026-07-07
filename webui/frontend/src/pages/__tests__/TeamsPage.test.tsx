import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TeamsPage from '../TeamsPage';

// Mock the global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('TeamsPage', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  it('renders correctly and opens the create modal', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });
    render(<TeamsPage />);

    // Check loading indicator shows and disappears
    await waitFor(() => {
        expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });

    const createBtns = screen.getAllByRole('button', { name: /create team/i });
    fireEvent.click(createBtns[0]);

    // Verify modal opens
    expect(screen.getByRole('dialog', { name: /create new team/i })).toBeInTheDocument();
  });

  it('opens the confirm delete modal and processes deletion', async () => {
    mockFetch.mockImplementation(async (url) => {
        if (url === '/teams/export?format=json') {
            return {
                ok: true,
                json: async () => ({
                    'test-team': { id: 'test-team', description: 'Testing team', llm_profile: 'default' }
                }),
            };
        }
        return { ok: true, json: async () => ({}) };
    });

    render(<TeamsPage />);

    const teamTitle = await screen.findByText('test-team');
    expect(teamTitle).toBeInTheDocument();

    // Instead of querying svg, we will look up the text 'Edit (demo)' which is close to the delete button,
    // actually wait, let's just add aria-label="Delete Team" in the TeamsPage.tsx component properly on the button instead of SVG.
    // Or we just find the 3rd button. There are 2 header buttons, then 2 buttons per team.

    // eslint-disable-next-line testing-library/no-node-access
    const deleteButton = screen.getAllByRole('button').find(b => b.querySelector('.lucide-trash2'));

    if (deleteButton) {
      fireEvent.click(deleteButton);
    } else {
        throw new Error('Delete button not found');
    }

    expect(screen.getByText('Delete Team')).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: 'Delete' });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/teams/', expect.objectContaining({
        method: 'POST',
      }));
    });
  });
});
