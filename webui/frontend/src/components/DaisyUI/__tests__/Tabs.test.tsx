import { render, screen, fireEvent } from '@testing-library/react';
import { Tabs } from '../Tabs';
import { vi } from 'vitest';

describe('Tabs Accessibility', () => {
  test('keyboard navigation allows Home and End keys', () => {
    const tabs = [
      { key: 'tab1', label: 'Tab 1' },
      { key: 'tab2', label: 'Tab 2' },
      { key: 'tab3', label: 'Tab 3' },
    ];
    let activeTab = 'tab2';
    const onChange = vi.fn((key) => { activeTab = key; });

    render(<Tabs tabs={tabs} activeTab={activeTab} onChange={onChange} />);

    const tab2 = screen.getByRole('tab', { name: 'Tab 2' });

    // Press End key on middle tab
    fireEvent.keyDown(tab2, { key: 'End' });
    expect(onChange).toHaveBeenLastCalledWith('tab3');

    // Press Home key
    fireEvent.keyDown(tab2, { key: 'Home' });
    expect(onChange).toHaveBeenLastCalledWith('tab1');
  });
});
