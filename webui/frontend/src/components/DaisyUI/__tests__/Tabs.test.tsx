import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Tabs } from '../Tabs';

describe('Tabs Accessibility and Keyboard Navigation', () => {
  const tabs = [
    { key: 'tab1', label: 'Tab 1' },
    { key: 'tab2', label: 'Tab 2', disabled: true },
    { key: 'tab3', label: 'Tab 3' },
    { key: 'tab4', label: 'Tab 4' }
  ];

  it('navigates to first non-disabled tab on Home key', () => {
    const handleChange = vi.fn();
    render(<Tabs tabs={tabs} activeTab="tab3" onChange={handleChange} />);

    const tab3 = screen.getByRole('tab', { name: 'Tab 3' });
    fireEvent.keyDown(tab3, { key: 'Home' });

    expect(handleChange).toHaveBeenCalledWith('tab1');
  });

  it('navigates to last non-disabled tab on End key', () => {
    const handleChange = vi.fn();
    render(<Tabs tabs={tabs} activeTab="tab1" onChange={handleChange} />);

    const tab1 = screen.getByRole('tab', { name: 'Tab 1' });
    fireEvent.keyDown(tab1, { key: 'End' });

    expect(handleChange).toHaveBeenCalledWith('tab4');
  });

  it('skips disabled tabs with Arrow keys', () => {
    const handleChange = vi.fn();
    render(<Tabs tabs={tabs} activeTab="tab1" onChange={handleChange} />);

    const tab1 = screen.getByRole('tab', { name: 'Tab 1' });
    fireEvent.keyDown(tab1, { key: 'ArrowRight' });

    expect(handleChange).toHaveBeenCalledWith('tab3');
  });
});
