import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Modal } from '../Modal';
import { vi } from 'vitest';

describe('Modal Accessibility', () => {
  beforeEach(() => {
    // jsdom doesn't implement showModal/close
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();
  });

  test('when modal is open, it traps focus or sets correct aria attributes', async () => {
    render(<Modal isOpen={true} onClose={() => {}} title="Test Modal">
      <button>Inside button 1</button>
      <button>Inside button 2</button>
    </Modal>);

    // Check for proper dialog roles
    const dialog = screen.getByRole('dialog', { hidden: true });
    expect(dialog).toBeInTheDocument();

    // Test for title aria-labelledby
    const title = screen.getByText('Test Modal');
    expect(dialog).toHaveAttribute('aria-labelledby', title.id);

    const firstElement = screen.getByText('Inside button 1');
    const lastElement = screen.getByText('close'); // "close" is actually the last button due to modal-backdrop form

    // Simulate Tab key to test trap moving back to first
    lastElement.focus();
    fireEvent.keyDown(dialog, { key: 'Tab' });

    await waitFor(() => {
        expect(firstElement).toHaveFocus();
    });

    // Simulate Shift+Tab key to test trap moving back to last
    firstElement.focus();
    fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true });

    await waitFor(() => {
        expect(lastElement).toHaveFocus();
    });
  });
});
