import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Pagination } from '../Pagination';

describe('Pagination Component', () => {
  it('adds aria-current="page" to the active page button', () => {
    const onPageChange = vi.fn();
    render(<Pagination currentPage={2} totalPages={5} onPageChange={onPageChange} />);

    // Get the active button (page 2)
    const activeBtn = screen.getByRole('button', { name: '2' });

    // It should have aria-current="page"
    expect(activeBtn).toHaveAttribute('aria-current', 'page');
    expect(activeBtn).toHaveClass('btn-active');

    // Get an inactive button (page 3)
    const inactiveBtn = screen.getByRole('button', { name: '3' });

    // It should not have aria-current="page"
    expect(inactiveBtn).not.toHaveAttribute('aria-current', 'page');
  });
});
