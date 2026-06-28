import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Modal } from '../Modal';

describe('Modal Accessibility and Focus Restoration', () => {
  it('captures document.activeElement before opening and restores it on close', async () => {
    // Setup a focusable element outside the modal
    render(
      <div>
        <button id="trigger-btn">Open Modal</button>
      </div>
    );
    const triggerBtn = screen.getByRole('button', { name: 'Open Modal' });
    triggerBtn.focus();
    // eslint-disable-next-line testing-library/no-node-access
    expect(document.activeElement).toBe(triggerBtn);

    // Open the modal
    const onClose = vi.fn();
    const { rerender } = render(
      <div>
        <button id="trigger-btn">Open Modal</button>
        <Modal isOpen={true} onClose={onClose} title="Test Modal">
          <p>Modal content</p>
        </Modal>
      </div>
    );

    // Dialog should be in the document
    expect(screen.getByRole('dialog', { hidden: true })).toBeInTheDocument();

    // Close the modal
    rerender(
      <div>
        <button id="trigger-btn">Open Modal</button>
        <Modal isOpen={false} onClose={onClose} title="Test Modal">
          <p>Modal content</p>
        </Modal>
      </div>
    );

    // Wait for the focus to be restored
    await waitFor(() => {
        // eslint-disable-next-line testing-library/no-node-access
        expect(document.activeElement).toBe(triggerBtn);
    });
  });
});
