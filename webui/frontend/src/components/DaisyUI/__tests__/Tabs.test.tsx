import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Tabs, VerticalTabs } from '../Tabs';

describe('Tabs Keyboard Navigation', () => {
  const tabs = [
    { key: 'tab1', label: 'Tab 1' },
    { key: 'tab2', label: 'Tab 2' },
    { key: 'tab3', label: 'Tab 3', disabled: true },
    { key: 'tab4', label: 'Tab 4' },
  ];

  it('navigates with ArrowRight, skipping disabled tabs', () => {
    const onChange = vi.fn();
    render(<Tabs tabs={tabs} activeTab="tab1" onChange={onChange} />);

    const firstTab = screen.getByRole('tab', { name: 'Tab 1' });
    fireEvent.keyDown(firstTab, { key: 'ArrowRight' });

    expect(onChange).toHaveBeenCalledWith('tab2');

    // Simulate active tab moved to tab2, arrow right should skip tab3
    render(<Tabs tabs={tabs} activeTab="tab2" onChange={onChange} />);
    const secondTab = screen.getAllByRole('tab', { name: 'Tab 2' })[1] || screen.getAllByRole('tab', { name: 'Tab 2' })[0];
    fireEvent.keyDown(secondTab, { key: 'ArrowRight' });
    expect(onChange).toHaveBeenCalledWith('tab4');
  });

  it('navigates with Home and End', () => {
    const onChange = vi.fn();
    render(<Tabs tabs={tabs} activeTab="tab2" onChange={onChange} />);

    const secondTab = screen.getByRole('tab', { name: 'Tab 2' });
    fireEvent.keyDown(secondTab, { key: 'Home' });
    expect(onChange).toHaveBeenCalledWith('tab1');

    fireEvent.keyDown(secondTab, { key: 'End' });
    expect(onChange).toHaveBeenCalledWith('tab4');
  });
});

describe('VerticalTabs Keyboard Navigation', () => {
  const tabs = [
    { key: 'tab1', label: 'Tab 1', content: <p>One</p> },
    { key: 'tab2', label: 'Tab 2', content: <p>Two</p> },
    { key: 'tab3', label: 'Tab 3', content: <p>Three</p>, disabled: true },
    { key: 'tab4', label: 'Tab 4', content: <p>Four</p> },
  ];

  it('exposes a vertical tablist and moves with ArrowDown, skipping disabled', () => {
    const onChange = vi.fn();
    render(<VerticalTabs tabs={tabs} activeTab="tab1" onChange={onChange} />);

    expect(screen.getByRole('tablist')).toHaveAttribute('aria-orientation', 'vertical');

    const firstTab = screen.getByRole('tab', { name: 'Tab 1' });
    fireEvent.keyDown(firstTab, { key: 'ArrowDown' });
    expect(onChange).toHaveBeenCalledWith('tab2');

    render(<VerticalTabs tabs={tabs} activeTab="tab2" onChange={onChange} />);
    const secondTabs = screen.getAllByRole('tab', { name: 'Tab 2' });
    const secondTab = secondTabs[secondTabs.length - 1];
    fireEvent.keyDown(secondTab, { key: 'ArrowDown' });
    expect(onChange).toHaveBeenCalledWith('tab4');
  });
});
