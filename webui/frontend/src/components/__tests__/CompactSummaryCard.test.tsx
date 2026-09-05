import { createEvent, fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CompactSummaryCard } from '../CompactSummaryCard'

describe('CompactSummaryCard (REQ-213)', () => {
  it('right-click opens the DaisyUI menu and suppresses the browser default', () => {
    render(<CompactSummaryCard body="outer digest" meta="Replaced 2 turns" />)

    const card = screen.getByTestId('chat-summary')
    const ev = createEvent.contextMenu(card)
    fireEvent(card, ev)
    expect(ev.defaultPrevented).toBe(true)

    const menu = screen.getByTestId('compacted-card-context-menu')
    expect(menu).toHaveClass('menu')
    expect(screen.getByRole('menuitem', { name: 'Collapse' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Copy' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Remove from view' })).toHaveClass('text-error')
  })

  it('Collapse hides the summary body; Expand reveals it again', () => {
    render(<CompactSummaryCard body="outer digest" />)
    expect(screen.getByTestId('chat-summary-content')).toHaveTextContent('outer digest')

    fireEvent.contextMenu(screen.getByTestId('chat-summary'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Collapse' }))
    expect(screen.queryByTestId('chat-summary-content')).not.toBeInTheDocument()
    expect(screen.queryByTestId('compacted-card-context-menu')).not.toBeInTheDocument()

    fireEvent.contextMenu(screen.getByTestId('chat-summary'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Expand' }))
    expect(screen.getByTestId('chat-summary-content')).toHaveTextContent('outer digest')
  })

  it('Copy writes the full underlying summary text', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    render(
      <CompactSummaryCard
        body="digest"
        compacted={[{ role: 'user', text: 'Ship it' }]}
      />,
    )
    fireEvent.contextMenu(screen.getByTestId('chat-summary'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Copy' }))
    expect(writeText).toHaveBeenCalledWith('digest\n\n---\n[user]: Ship it')
  })

  it('Remove from view hides the chip without a persist callback', () => {
    render(<CompactSummaryCard body="digest" />)
    fireEvent.contextMenu(screen.getByTestId('chat-summary'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Remove from view' }))
    expect(screen.queryByTestId('chat-summary')).not.toBeInTheDocument()
  })

  it('Remove from view notifies the parent so Chat can hide without rewriting disk', () => {
    const onRemove = vi.fn()
    render(<CompactSummaryCard body="digest" onRemove={onRemove} />)
    fireEvent.contextMenu(screen.getByTestId('chat-summary'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Remove from view' }))
    expect(onRemove).toHaveBeenCalledTimes(1)
  })
})
