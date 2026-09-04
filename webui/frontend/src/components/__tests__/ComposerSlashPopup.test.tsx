import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ComposerSlashPopup } from '../ComposerSlashPopup'
import { buildSlashCatalog, filterSlashItems } from '../../lib/slashMenu'

describe('ComposerSlashPopup', () => {
  const catalog = buildSlashCatalog()

  it('renders nothing when open is false', () => {
    const { container } = render(
      <ComposerSlashPopup
        open={false}
        query=""
        items={catalog}
        selectedIndex={0}
        onSelectIndex={vi.fn()}
        onSelectItem={vi.fn()}
      />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders Actions and Skills sections when query is empty', () => {
    const items = filterSlashItems(catalog, '', [])
    render(
      <ComposerSlashPopup
        open={true}
        query=""
        items={items}
        selectedIndex={0}
        onSelectIndex={vi.fn()}
        onSelectItem={vi.fn()}
      />,
    )

    expect(screen.getByTestId('composer-slash-popup')).toBeInTheDocument()
    expect(screen.getByText('Actions')).toBeInTheDocument()
    expect(screen.getByText('Skills')).toBeInTheDocument()
    expect(screen.getByText('Compact')).toBeInTheDocument()
    expect(screen.getByText('/compact')).toBeInTheDocument()
    expect(screen.getByText('Conventional Commit')).toBeInTheDocument()
  })

  it('renders Recent section when recentIds are provided with empty query', () => {
    const recentIds = ['compact']
    const items = filterSlashItems(catalog, '', recentIds)
    render(
      <ComposerSlashPopup
        open={true}
        query=""
        items={items}
        selectedIndex={0}
        onSelectIndex={vi.fn()}
        onSelectItem={vi.fn()}
        recentIds={recentIds}
      />,
    )

    const recentElements = screen.getAllByText('Recent')
    // Section title + badge
    expect(recentElements.length).toBeGreaterThanOrEqual(1)
  })

  it('displays empty state when items list is empty', () => {
    render(
      <ComposerSlashPopup
        open={true}
        query="nonexistent"
        items={[]}
        selectedIndex={0}
        onSelectIndex={vi.fn()}
        onSelectItem={vi.fn()}
      />,
    )

    expect(screen.getByTestId('slash-empty')).toHaveTextContent(
      'No matching skills or actions',
    )
  })

  it('calls onSelectItem when an item is clicked', () => {
    const onSelectItem = vi.fn()
    const items = filterSlashItems(catalog, '', [])
    render(
      <ComposerSlashPopup
        open={true}
        query=""
        items={items}
        selectedIndex={0}
        onSelectIndex={vi.fn()}
        onSelectItem={onSelectItem}
      />,
    )

    const compactBtn = screen.getByTestId('slash-item-compact')
    fireEvent.click(compactBtn)
    expect(onSelectItem).toHaveBeenCalledTimes(1)
    expect(onSelectItem).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'compact', kind: 'action' }),
    )
  })

  it('calls onSelectIndex on mouse enter and reflects selectedIndex', () => {
    const onSelectIndex = vi.fn()
    const items = filterSlashItems(catalog, '', [])
    render(
      <ComposerSlashPopup
        open={true}
        query=""
        items={items}
        selectedIndex={1}
        onSelectIndex={onSelectIndex}
        onSelectItem={vi.fn()}
      />,
    )

    const options = screen.getAllByRole('option')
    expect(options[1]).toHaveAttribute('aria-selected', 'true')

    fireEvent.mouseEnter(options[0])
    expect(onSelectIndex).toHaveBeenCalledWith(0)
  })
})
