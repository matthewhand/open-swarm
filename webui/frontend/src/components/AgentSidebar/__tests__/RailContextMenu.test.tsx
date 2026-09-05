import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { RailContextMenu } from '../RailContextMenu'

describe('RailContextMenu', () => {
  it('renders visible items and hides hidden ones', () => {
    const onSelect = vi.fn()
    render(
      <RailContextMenu
        agentName="cli_agent"
        x={10}
        y={20}
        items={[
          { id: 'select-session', label: 'Select session', icon: null, onSelect, testId: 'rail-menu-select-session' },
          { id: 'hidden', label: 'Secret', icon: null, onSelect: vi.fn(), hidden: true },
          { id: 'hide', label: 'Hide from sidebar', icon: null, onSelect: vi.fn() },
        ]}
      />,
    )
    const menu = screen.getByRole('menu', { name: 'Actions for cli_agent' })
    expect(menu).toHaveAttribute('data-testid', 'rail-context-menu')
    expect(screen.getByTestId('rail-menu-select-session')).toHaveTextContent('Select session')
    expect(screen.queryByRole('menuitem', { name: 'Secret' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('menuitem', { name: 'Select session' }))
    expect(onSelect).toHaveBeenCalledTimes(1)
  })
})
