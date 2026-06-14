import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Modal, ConfirmModal } from '../Modal';
import { Input } from '../Input';
import { Select } from '../Select';
import { Textarea } from '../Textarea';
import { Button } from '../Button';
import { LoadingSpinner } from '../Loading';
import { Pagination } from '../Pagination';
import { Tabs } from '../Tabs';

describe('Modal Accessibility', () => {
  it('should use HTML5 dialog and sync state', () => {
    const { rerender } = render(<Modal isOpen={false} onClose={() => {}}>Content</Modal>);
    const dialog = screen.getByRole('dialog', { hidden: true });
    expect(dialog).not.toHaveAttribute('open');

    rerender(<Modal isOpen={true} onClose={() => {}}>Content</Modal>);
    expect(dialog).toHaveAttribute('open');
  });

  it('should link title via aria-labelledby', () => {
    render(<Modal isOpen={true} onClose={() => {}} title="My Title">Content</Modal>);
    const dialog = screen.getByRole('dialog');
    const title = screen.getByText('My Title');
    expect(dialog).toHaveAttribute('aria-labelledby', title.id);
  });

  it('should pass loading state to ConfirmModal confirm button', () => {
    render(
      <ConfirmModal isOpen={true} onClose={() => {}} onConfirm={() => {}} isConfirmLoading={true}>
        Content
      </ConfirmModal>
    );
    const confirmButton = screen.getByRole('button', { name: /confirm/i });
    expect(confirmButton).toHaveAttribute('aria-busy', 'true');
    expect(confirmButton).toHaveAttribute('aria-disabled', 'true');
  });
});

describe('Form Control Accessibility', () => {
  it('should link Input label and error deterministically', () => {
    render(<Input label="My Label" error="My Error" />);
    // Testing-library sees both "My Label" and "My Error" as part of the accessible name
    // when they are both associated labels, but since `aria-describedby` is used for the error,
    // the name itself might just be "My Label" depending on how screen readers compose it.
    // However, the error output above showed it evaluated to `Name "My Label My Error":`
    // This is because DaisyUI forms put both label and error spans inside their own `<label>`
    // tags pointing to the same `id`. Testing Library correctly concatenates all label text.
    const input = screen.getByRole('textbox', { name: 'My Label My Error' });
    const error = screen.getByText('My Error');

    expect(input).toBeInTheDocument();

    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute('aria-describedby', error.id);
  });

  it('should link Select label and error deterministically', () => {
    render(
      <Select label="My Select" error="Select Error">
        <option>Option</option>
      </Select>
    );
    const select = screen.getByRole('combobox', { name: 'My Select Select Error' });
    const error = screen.getByText('Select Error');

    expect(select).toBeInTheDocument();

    expect(select).toHaveAttribute('aria-invalid', 'true');
    expect(select).toHaveAttribute('aria-describedby', error.id);
  });

  it('should link Textarea label and error deterministically', () => {
    render(<Textarea label="My Textarea" error="Text Error" />);
    const textarea = screen.getByRole('textbox', { name: 'My Textarea Text Error' });
    const error = screen.getByText('Text Error');

    expect(textarea).toBeInTheDocument();

    expect(textarea).toHaveAttribute('aria-invalid', 'true');
    expect(textarea).toHaveAttribute('aria-describedby', error.id);
  });
});

describe('Async Loading Accessibility', () => {
  it('LoadingSpinner should have role="status"', () => {
    render(<LoadingSpinner />);
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveAttribute('aria-label', 'Loading');
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

describe('Pagination Accessibility', () => {
  it('should wrap in nav and indicate current page', () => {
    render(<Pagination currentPage={2} totalPages={5} onPageChange={() => {}} />);

    // Check for nav wrapper
    const nav = screen.getByRole('navigation', { name: 'Pagination' });
    expect(nav).toBeInTheDocument();

    // The button for page 2 should have aria-current="page"
    const activePageBtn = screen.getByRole('button', { name: '2' });
    expect(activePageBtn).toHaveAttribute('aria-current', 'page');

    // Other pages should not
    const inactivePageBtn = screen.getByRole('button', { name: '1' });
    expect(inactivePageBtn).not.toHaveAttribute('aria-current');
  });
});

describe('Tabs Accessibility', () => {
  it('should navigate to first/last tab on Home/End keys', () => {
    const onChangeMock = vi.fn();
    const tabs = [
      { key: 'tab1', label: 'Tab 1' },
      { key: 'tab2', label: 'Tab 2' },
      { key: 'tab3', label: 'Tab 3' },
    ];

    render(<Tabs tabs={tabs} activeTab="tab2" onChange={onChangeMock} />);

    const activeTab = screen.getByRole('tab', { selected: true });

    // Press Home
    fireEvent.keyDown(activeTab, { key: 'Home' });
    expect(onChangeMock).toHaveBeenCalledWith('tab1');

    // Press End
    fireEvent.keyDown(activeTab, { key: 'End' });
    expect(onChangeMock).toHaveBeenCalledWith('tab3');
  });
});
