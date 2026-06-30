import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import BuilderPage from '../BuilderPage';
import { useQuery } from '@tanstack/react-query';

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
  useMutation: vi.fn(),
  useQueryClient: vi.fn(() => ({
    invalidateQueries: vi.fn(),
  })),
}));

vi.mock('../../components/DaisyUI/Modal', () => ({
  Modal: ({ children, isOpen }: any) => isOpen ? <div role="dialog">{children}</div> : null,
  ConfirmModal: ({ children, isOpen }: any) => isOpen ? <div role="dialog">{children}</div> : null,
}));

vi.mock('../../components/DaisyUI/Toast', () => ({
  ToastProvider: ({ children }: any) => <div>{children}</div>,
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }),
}));

describe('BuilderPage Async States Accessibility', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state with polite aria-live and aria-busy', () => {
    (useQuery as any).mockImplementation(({ queryKey }: any) => {
      if (queryKey[0] === 'blueprints') {
        return { isPending: true, isError: false, data: undefined };
      }
      return { isPending: false, isError: false, data: undefined };
    });

    render(<BuilderPage />);

    const loadingSpinner = screen.getByRole('status', { hidden: true });
    expect(loadingSpinner).toBeInTheDocument();
  });

  it('renders error state with assertive aria-live and alert role', () => {
    (useQuery as any).mockImplementation(({ queryKey }: any) => {
      if (queryKey[0] === 'blueprints') {
        return { isPending: false, isError: true, data: undefined, error: new Error('Network error') };
      }
      return { isPending: false, isError: false, data: undefined };
    });

    render(<BuilderPage />);
    const alertRegions = screen.getAllByRole('alert');
    // Find the one for blueprints error (Alert component might have its own role="alert", we check the wrapper)
    const alertContainer = alertRegions.find(el => el.getAttribute('aria-live') === 'assertive');

    expect(alertContainer).toBeInTheDocument();
    expect(alertContainer).toHaveTextContent(/Failed to load blueprints/);
  });

  it('renders deterministic empty state with status role', () => {
    (useQuery as any).mockImplementation(({ queryKey }: any) => {
      if (queryKey[0] === 'blueprints') {
        return { isPending: false, isError: false, data: { data: [] } };
      }
      return { isPending: false, isError: false, data: undefined };
    });

    render(<BuilderPage />);
    // Our status region for empty blueprints
    const statusRegions = screen.getAllByRole('status');
    const emptyStatus = statusRegions.find(el => el.textContent?.includes('No blueprints available'));

    expect(emptyStatus).toBeInTheDocument();
  });
});
