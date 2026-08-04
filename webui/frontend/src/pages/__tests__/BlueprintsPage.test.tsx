import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, afterEach } from 'vitest'
import BlueprintsPage from '../BlueprintsPage'

// Mock fetch
const originalFetch = global.fetch;

describe('BlueprintsPage', () => {
  afterEach(() => {
     global.fetch = originalFetch;
  });

  it('shows generic loading states and correct aria implementations', async () => {
    // Basic test
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({})
    });

    render(<BlueprintsPage />);

    // eslint-disable-next-line testing-library/prefer-find-by
    await waitFor(() => {
        expect(screen.getAllByRole('status').length).toBeGreaterThan(0);
    });
  });
});
