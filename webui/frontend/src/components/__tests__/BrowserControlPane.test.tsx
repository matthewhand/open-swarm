import { describe, it, expect } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import BrowserControlPane from '../BrowserControlPane'

describe('BrowserControlPane', () => {
  it('opens with Browser (this machine) selected as the default', () => {
    render(<BrowserControlPane />)
    fireEvent.click(screen.getByRole('button', { name: 'Browser control' }))
    expect(screen.getByRole('dialog', { name: 'Browser control' })).toBeInTheDocument()
    const local = screen.getByRole('button', { name: /Browser \(this machine\)/i })
    expect(local).toHaveAttribute('aria-pressed', 'true')
    expect(local).toHaveAttribute('data-target', 'this_machine')
    expect(local).not.toHaveAttribute('data-todo', 'true')
    expect(screen.getByText('Default')).toBeInTheDocument()
  })

  it('keeps sandbox and SaaS greyed TODO — clickable WIP, not selected', () => {
    render(<BrowserControlPane />)
    fireEvent.click(screen.getByRole('button', { name: 'Browser control' }))

    const sandbox = screen.getByRole('button', { name: /Sandbox \/ Docker/i })
    const saas = screen.getByRole('button', { name: /^SaaS/i })
    expect(sandbox).toHaveClass('os-browser-target--todo')
    expect(saas).toHaveClass('os-browser-target--todo')
    expect(sandbox).toHaveAttribute('data-todo', 'true')
    expect(saas).toHaveAttribute('data-todo', 'true')
    expect(sandbox).toHaveAttribute('aria-pressed', 'false')
    expect(saas).toHaveAttribute('aria-pressed', 'false')

    fireEvent.click(sandbox)
    expect(screen.getByText(/Sandbox \/ Docker browser provider is TODO — not wired/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Browser \(this machine\)/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(sandbox).toHaveAttribute('aria-pressed', 'false')

    fireEvent.click(saas)
    expect(screen.getByText(/SaaS browser provider is TODO — not wired/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Browser \(this machine\)/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('does not expose enable/sandbox wiring or a live preview checkout', () => {
    render(<BrowserControlPane />)
    fireEvent.click(screen.getByRole('button', { name: 'Browser control' }))
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    expect(screen.queryByText(/live preview checkout/i)).not.toBeInTheDocument()
    expect(screen.getByText(/No live preview/i)).toBeInTheDocument()
    expect(screen.getByText(/#341/)).toBeInTheDocument()
  })
})
