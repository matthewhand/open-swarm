import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Modal } from '../Modal';
import { Input } from '../Input';
import { Select } from '../Select';
import { Textarea } from '../Textarea';
import { Button } from '../Button';
import { Alert } from '../Alert';
import { LoadingOverlay, LoadingSpinner } from '../Loading';
import { ToastProvider, useToast } from '../Toast';
import { useEffect } from 'react';

describe('Modal Accessibility', () => {
  it('should use HTML5 dialog and sync state', () => {
    const { rerender } = render(<Modal isOpen={false} onClose={() => {}}>Content</Modal>);
    const dialog = screen.getByRole('dialog', { hidden: true });
    expect(dialog).not.toHaveClass('modal-open');

    rerender(<Modal isOpen={true} onClose={() => {}}>Content</Modal>);
    const openDialog = screen.getByRole('dialog', { hidden: true });
    expect(openDialog).toHaveClass('modal-open');
  });

  it('should link title via aria-labelledby', () => {
    render(<Modal isOpen={true} onClose={() => {}} title="My Title">Content</Modal>);
    const dialog = screen.getByRole('dialog');
    const title = screen.getByText('My Title');
    expect(dialog).toHaveAttribute('aria-labelledby', title.id);
  });
});

describe('Form Control Accessibility', () => {
  // The error message renders as a role="alert" span OUTSIDE the <label>, so
  // it must not leak into the control's accessible name; aria-describedby
  // carries the association for assistive tech.
  it('links Input label and error without polluting the accessible name', () => {
    render(<Input label="My Label" error="My Error" />);
    const input = screen.getByRole('textbox', { name: 'My Label' });
    const error = screen.getByRole('alert');

    expect(input).toBeInTheDocument();
    expect(error).toHaveTextContent('My Error');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute('aria-describedby', error.id);
  });

  it('links Select label and error without polluting the accessible name', () => {
    render(
      <Select label="My Select" error="Select Error">
        <option>Option</option>
      </Select>
    );
    const select = screen.getByRole('combobox', { name: 'My Select' });
    const error = screen.getByRole('alert');

    expect(select).toBeInTheDocument();
    expect(error).toHaveTextContent('Select Error');
    expect(select).toHaveAttribute('aria-invalid', 'true');
    expect(select).toHaveAttribute('aria-describedby', error.id);
  });

  it('links Textarea label and error without polluting the accessible name', () => {
    render(<Textarea label="My Textarea" error="Text Error" />);
    const textarea = screen.getByRole('textbox', { name: 'My Textarea' });
    const error = screen.getByRole('alert');

    expect(textarea).toBeInTheDocument();
    expect(error).toHaveTextContent('Text Error');
    expect(textarea).toHaveAttribute('aria-invalid', 'true');
    expect(textarea).toHaveAttribute('aria-describedby', error.id);
  });
});

describe('Alert Accessibility', () => {
  it('uses role="status" for info and success by default', () => {
    const { rerender } = render(<Alert type="info">Heads up</Alert>);
    expect(screen.getByRole('status')).toHaveTextContent('Heads up');

    rerender(<Alert type="success">Saved</Alert>);
    expect(screen.getByRole('status')).toHaveTextContent('Saved');
  });

  it('uses role="alert" for warning and error by default', () => {
    const { rerender } = render(<Alert type="warning">Careful</Alert>);
    expect(screen.getByRole('alert')).toHaveTextContent('Careful');

    rerender(<Alert type="error">Failed</Alert>);
    expect(screen.getByRole('alert')).toHaveTextContent('Failed');
  });

  it('marks decorative icons as aria-hidden', () => {
    render(
      <Alert type="error" icon={<span data-testid="alert-icon">!</span>}>
        Boom
      </Alert>,
    );
    expect(screen.getByTestId('alert-icon').parentElement).toHaveAttribute(
      'aria-hidden',
      'true',
    );
  });

  it('allows an explicit role override', () => {
    render(
      <Alert type="error" role="status">
        Soft error
      </Alert>,
    );
    expect(screen.getByRole('status')).toHaveTextContent('Soft error');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('Toast Accessibility', () => {
  function FireToast({ type }: { type: 'info' | 'error' }) {
    const { error, info } = useToast();
    useEffect(() => {
      if (type === 'error') {
        error('Err title', 'Something failed');
      } else {
        info('Info title', 'Hello');
      }
      // Fire once on mount; do not depend on toast helpers (new refs each render).
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [type]);
    return null;
  }

  it('announces info toasts with role=status and aria-live=polite', () => {
    render(
      <ToastProvider>
        <FireToast type="info" />
      </ToastProvider>,
    );
    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-live', 'polite');
    expect(status).toHaveTextContent('Info title');
  });

  it('announces error toasts assertively', () => {
    render(
      <ToastProvider>
        <FireToast type="error" />
      </ToastProvider>,
    );
    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-live', 'assertive');
    expect(status).toHaveTextContent('Err title');
  });
});

describe('Async Loading Accessibility', () => {
  it('LoadingSpinner should have role="status"', () => {
    render(<LoadingSpinner />);
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveAttribute('aria-label', 'Loading');
  });

  it('LoadingOverlay announces as status, not dialog', () => {
    render(<LoadingOverlay message="Fetching data" />);
    const overlay = screen.getByRole('status', { name: 'Fetching data' });
    expect(overlay).toHaveAttribute('aria-live', 'polite');
    expect(overlay).toHaveAttribute('aria-busy', 'true');
    expect(overlay).not.toHaveAttribute('aria-modal');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('Button should announce busy state when loading', () => {
    render(<Button loading={true}>Submit</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toHaveAttribute('aria-disabled', 'true');

    // Check for sr-only text
    expect(screen.getByText('Loading')).toHaveClass('sr-only');
  });
});
