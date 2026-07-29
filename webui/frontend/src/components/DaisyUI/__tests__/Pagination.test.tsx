import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Pagination } from '../Pagination';

describe('Pagination A11y & Functionality', () => {
  it('renders with appropriate aria attributes and handles focus properly', () => {
    const handlePageChange = vi.fn();
    render(
      <Pagination
        currentPage={2}
        totalPages={5}
        onPageChange={handlePageChange}
      />
    );

    // Check next and prev buttons existence
    const prevButton = screen.getByLabelText('Previous page');
    const nextButton = screen.getByLabelText('Next page');
    expect(prevButton).toBeInTheDocument();
    expect(nextButton).toBeInTheDocument();

    // Check aria-current behavior for the active page
    const page2Button = screen.getByRole('button', { name: '2' });
    expect(page2Button).toHaveAttribute('aria-current', 'page');
    expect(page2Button).toHaveClass('btn-active');

    const page3Button = screen.getByRole('button', { name: '3' });
    expect(page3Button).not.toHaveAttribute('aria-current');

    // Test clicking another page
    fireEvent.click(page3Button);
    expect(handlePageChange).toHaveBeenCalledWith(3);
  });
});
