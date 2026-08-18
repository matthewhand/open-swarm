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

  it('renders focusable button backdrop and calls onClose when clicked', async () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={onClose} title="Backdrop Test">
        <p>Backdrop content</p>
      </Modal>
    );

    const backdrop = screen.getByRole('button', { name: 'Close modal' });
    expect(backdrop).toBeInTheDocument();
    expect(backdrop).toHaveClass('modal-backdrop');
    expect(backdrop).toHaveAttribute('tabIndex', '-1');

    backdrop.click();
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('keeps FocusTrap mounted and toggles active with isOpen', () => {
    const onClose = vi.fn();
    const { rerender } = render(
      <Modal isOpen={false} onClose={onClose} title="Trap Test">
        <button type="button">Inside</button>
      </Modal>
    );

    const dialog = screen.getByRole('dialog', { hidden: true });
    expect(dialog).not.toHaveClass('modal-open');
    expect(dialog).not.toHaveAttribute('aria-modal');

    rerender(
      <Modal isOpen={true} onClose={onClose} title="Trap Test">
        <button type="button">Inside</button>
      </Modal>
    );

    const openDialog = screen.getByRole('dialog', { hidden: true });
    expect(openDialog).toHaveClass('modal-open');
    expect(openDialog).toHaveAttribute('aria-modal', 'true');
  });

  it('exposes aria-label when title is omitted', () => {
    render(
      <Modal isOpen={true} onClose={() => {}} aria-label="Untitled dialog">
        <p>Body</p>
      </Modal>
    );
    expect(screen.getByRole('dialog', { hidden: true })).toHaveAttribute(
      'aria-label',
      'Untitled dialog'
    );
  });
});
