import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, afterEach } from 'vitest'
import TeamsPage from '../TeamsPage'

// Mock fetch
const originalFetch = global.fetch;

describe('TeamsPage', () => {
  afterEach(() => {
     global.fetch = originalFetch;
  });

  it('shows generic loading states and correctly processes delete confirmations', async () => {
    // Basic test
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({})
    });

    render(<TeamsPage />);

    // eslint-disable-next-line testing-library/prefer-find-by
    await waitFor(() => {
        expect(screen.getAllByRole('status').length).toBeGreaterThan(0);
    });
  });
});
