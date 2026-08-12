import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Modal } from '../Modal';

describe('Modal Accessibility and Focus Restoration', () => {
  it('captures document.activeElement before opening and restores it on close', async () => {
    render(
      <div>
        <button id="trigger-btn">Open Modal</button>
      </div>
    );
    const triggerBtn = screen.getByRole('button', { name: 'Open Modal' });
    triggerBtn.focus();
    // eslint-disable-next-line testing-library/no-node-access
    expect(document.activeElement).toBe(triggerBtn);

    const onClose = vi.fn();
    const { rerender } = render(
      <div>
        <button id="trigger-btn">Open Modal</button>
        <Modal isOpen={true} onClose={onClose} title="Test Modal">
          <p>Modal content</p>
        </Modal>
      </div>
    );

    expect(screen.getByRole('dialog', { hidden: true })).toBeInTheDocument();

    rerender(
      <div>
        <button id="trigger-btn">Open Modal</button>
        <Modal isOpen={false} onClose={onClose} title="Test Modal">
          <p>Modal content</p>
        </Modal>
      </div>
    );

    await waitFor(() => {
      // eslint-disable-next-line testing-library/no-node-access
      expect(document.activeElement).toBe(triggerBtn);
    });
  });

  it('renders native form dialog backdrop and calls onClose when clicked', async () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={onClose} title="Backdrop Test">
        <p>Backdrop content</p>
      </Modal>
    );

    // Form element has the modal-backdrop class
    // We cannot reliably select by role="form" here unless we give it an accessible name,
    // so we can find the close button, then find its parent form.
    const closeBtn = screen.getByRole('button', { name: 'close' });
    expect(closeBtn).toBeInTheDocument();
    expect(closeBtn).toHaveAttribute('tabIndex', '-1');

    // eslint-disable-next-line testing-library/no-node-access
    const form = closeBtn.closest('form');
    expect(form).toBeInTheDocument();
    expect(form).toHaveAttribute('method', 'dialog');
    expect(form).toHaveClass('modal-backdrop');

    closeBtn.click();
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
