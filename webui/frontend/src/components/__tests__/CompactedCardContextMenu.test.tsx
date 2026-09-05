import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import CompactedCardContextMenu from '../CompactedCardContextMenu'
import { compactedCardMenuItems } from '../../lib/compactedCardMenu'

describe('CompactedCardContextMenu (REQ-213)', () => {
  it('uses DaisyUI menu chrome matching the rail (#435) with danger last', () => {
    const onSelect = vi.fn()
    const onClose = vi.fn()
    render(
      <CompactedCardContextMenu
        label="Message from System"
        x={12}
        y={24}
        items={compactedCardMenuItems({ expanded: false })}
        onSelect={onSelect}
        onClose={onClose}
      />,
    )

    const menu = screen.getByTestId('compacted-card-context-menu')
    expect(menu).toHaveClass('menu')
    expect(menu).toHaveClass('menu-sm')
    expect(menu).toHaveClass('rounded-box')
    expect(menu).toHaveAttribute('role', 'menu')
    expect(menu).toHaveAccessibleName('Actions for Message from System')

    const items = within(menu).getAllByRole('menuitem')
    expect(items.map((el) => el.textContent)).toEqual(['Expand', 'Copy', 'Remove from view'])
    for (const item of items) {
      expect(item.querySelector('[data-menu-icon]')).toBeTruthy()
    }
    const del = items.at(-1)!
    expect(del).toHaveClass('text-error')
    expect(del.querySelector('[data-menu-icon="delete"]')).toHaveClass('text-error')
    fireEvent.click(del)
    expect(onSelect).toHaveBeenCalledWith('delete')
  })

  it('shows Collapse when the card is already expanded', () => {
    render(
      <CompactedCardContextMenu
        label="Summary"
        x={0}
        y={0}
        items={compactedCardMenuItems({ expanded: true })}
        onSelect={() => undefined}
        onClose={() => undefined}
      />,
    )
    expect(screen.getByRole('menuitem', { name: 'Collapse' })).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Expand' })).not.toBeInTheDocument()
  })

  it('backdrop click and right-click close the menu and suppress the browser default', () => {
    const onClose = vi.fn()
    render(
      <CompactedCardContextMenu
        label="Summary"
        x={0}
        y={0}
        items={compactedCardMenuItems({ expanded: true })}
        onSelect={() => undefined}
        onClose={onClose}
      />,
    )
    const backdrop = screen.getByTestId('compacted-card-menu-backdrop')
    fireEvent.click(backdrop)
    expect(onClose).toHaveBeenCalledTimes(1)

    const ev = new MouseEvent('contextmenu', { bubbles: true, cancelable: true })
    backdrop.dispatchEvent(ev)
    expect(ev.defaultPrevented).toBe(true)
    expect(onClose).toHaveBeenCalledTimes(2)
  })
})
