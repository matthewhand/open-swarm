import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Accordion, AccordionItem } from '../Tabs';

describe('Accordion A11y & Structure', () => {
  it('should generate valid ARIA links and deterministic IDs for Accordion map', () => {
    const items = [
      { key: 'item-1', title: 'Header 1', content: 'Content 1' },
      { key: 'item-2', title: 'Header 2', content: 'Content 2' }
    ];

    render(<Accordion items={items} />);

    // In DaisyUI, Accordions use checkbox inputs natively
    const checkboxes = screen.getAllByRole('checkbox');
    const input1 = checkboxes[0];

    expect(input1).toBeInTheDocument();
    expect(input1).toHaveAttribute('aria-controls', 'accordion-panel-item-1');
    expect(input1).toHaveAttribute('aria-expanded', 'false');

    // Check if the region uses aria-labelledby correctly
    const regions = screen.getAllByRole('region');
    const panel1 = regions[0];
    expect(panel1).toBeInTheDocument();
    expect(panel1).toHaveAttribute('aria-labelledby', 'accordion-header-item-1');
  });

  it('should provide deterministic ID fallback via useId in standalone AccordionItem', () => {
    render(
      <AccordionItem title="Standalone Header">
        Standalone Content
      </AccordionItem>
    );

    const inputCheckbox = screen.getByRole('checkbox');
    const panelNode = screen.getByRole('region');

    expect(inputCheckbox).toBeInTheDocument();
    expect(panelNode).toBeInTheDocument();

    expect(inputCheckbox).toHaveAttribute('aria-controls');
    expect(panelNode).toHaveAttribute('aria-labelledby');

    const controlsId = inputCheckbox.getAttribute('aria-controls');
    const labelledById = panelNode.getAttribute('aria-labelledby');

    // Make sure they match and refer to each other properly
    expect(controlsId?.startsWith('panel-')).toBe(true);
    expect(labelledById?.startsWith('header-')).toBe(true);

    // Test that the ID isn't containing Math.random string '0.' pattern
    expect(controlsId).not.toContain('0.');
  });
});
