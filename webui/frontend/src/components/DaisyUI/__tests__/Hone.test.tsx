import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { Tabs } from '../Tabs';
import { useInfiniteScroll } from '../Pagination';
import { LoadingSpinner, LoadingOverlay } from '../Loading';
import { renderHook, act } from '@testing-library/react';

describe('Tabs Keyboard Operability', () => {
  it('should navigate to the first and last tabs using Home and End keys', async () => {
    const tabs = [
      { key: 'tab1', label: 'Tab 1' },
      { key: 'tab2', label: 'Tab 2' },
      { key: 'tab3', label: 'Tab 3' },
    ];
    const onChange = vi.fn();
    render(<Tabs tabs={tabs} activeTab="tab2" onChange={onChange} />);

    const tab2 = screen.getByRole('tab', { name: 'Tab 2' });
    tab2.focus();

    await userEvent.keyboard('{Home}');
    expect(onChange).toHaveBeenCalledWith('tab1');

    await userEvent.keyboard('{End}');
    expect(onChange).toHaveBeenCalledWith('tab3');
  });

  it('should gracefully handle disabled tabs during Home/End navigation', async () => {
    const tabs = [
      { key: 'tab1', label: 'Tab 1', disabled: true },
      { key: 'tab2', label: 'Tab 2' },
      { key: 'tab3', label: 'Tab 3', disabled: true },
      { key: 'tab4', label: 'Tab 4' },
    ];
    const onChange = vi.fn();
    render(<Tabs tabs={tabs} activeTab="tab2" onChange={onChange} />);

    const tab2 = screen.getByRole('tab', { name: 'Tab 2' });
    tab2.focus();

    await userEvent.keyboard('{Home}');
    // Tab 1 is disabled, so it should wrap forward to Tab 2
    expect(onChange).toHaveBeenCalledWith('tab2');

    await userEvent.keyboard('{End}');
    // Tab 4 is enabled, but let's say Tab 4 was disabled, it would wrap backwards to Tab 2
    expect(onChange).toHaveBeenCalledWith('tab4');
  });
});

describe('Pagination Async State & Type Safety', () => {
  it('should expose error state deterministically', async () => {
    const fetchFunction = vi.fn().mockRejectedValue(new Error('API Failure'));
    const { result } = renderHook(() => useInfiniteScroll<string>([]));

    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);

    await act(async () => {
      await result.current.loadMore(fetchFunction);
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe('API Failure');
    expect(result.current.isLoading).toBe(false);
  });
});

describe('Loading Enhancements', () => {
  it('LoadingSpinner should have aria-live and aria-busy', () => {
    render(<LoadingSpinner />);
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveAttribute('aria-live', 'polite');
    expect(spinner).toHaveAttribute('aria-busy', 'true');
  });

  it('LoadingOverlay should have aria-live and aria-busy', () => {
    render(<LoadingOverlay isLoading={true} message="Authenticating..." />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-live', 'polite');
    expect(dialog).toHaveAttribute('aria-busy', 'true');
  });
});
