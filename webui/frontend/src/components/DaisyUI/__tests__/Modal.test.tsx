import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { Modal, ConfirmModal } from '../Modal';

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
    // eslint-disable-next-line testing-library/no-node-access
    expect(backdrop.parentElement).toHaveClass('modal-backdrop');
    // eslint-disable-next-line testing-library/no-node-access
    expect(backdrop.parentElement?.tagName).toBe('FORM');
    // eslint-disable-next-line testing-library/no-node-access
    expect(backdrop.parentElement).toHaveAttribute('method', 'dialog');
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

describe('ConfirmModal Async State Integrity', () => {
  it('displays loading state and prevents double submissions', async () => {
    const user = userEvent.setup();
    let resolvePromise: () => void;
    const onConfirm = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolvePromise = resolve;
        })
    );

    render(
      <ConfirmModal isOpen={true} onClose={() => {}} onConfirm={onConfirm} confirmText="Submit" />
    );

    const submitBtn = screen.getByRole('button', { name: 'Submit' });

    await user.click(submitBtn);
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(submitBtn).toHaveAttribute('aria-busy', 'true');

    // Click again while submitting
    await user.click(submitBtn);
    expect(onConfirm).toHaveBeenCalledTimes(1); // should still be 1

    // Resolve the promise
    resolvePromise!();

    await waitFor(() => {
      expect(submitBtn).not.toHaveAttribute('aria-busy', 'true');
    });
  });

  it('displays deterministic error string on rejection', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn(() => Promise.reject(new Error('Network error')));

    render(
      <ConfirmModal isOpen={true} onClose={() => {}} onConfirm={onConfirm} confirmText="Submit" />
    );

    const submitBtn = screen.getByRole('button', { name: 'Submit' });
    await user.click(submitBtn);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Network error');
  });
});
