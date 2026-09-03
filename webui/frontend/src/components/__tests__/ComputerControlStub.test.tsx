import { describe, it, expect } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import {
  COMPUTER_CONTROL_WIP_COPY,
  ComputerControlStub,
} from '../ComputerControlStub'

describe('ComputerControlStub (REQ-27b)', () => {
  it('shows a computer/monitor control labeled Computer control', () => {
    render(<ComputerControlStub />)

    const trigger = screen.getByRole('button', { name: 'Computer control' })
    expect(trigger).toBeInTheDocument()
    expect(trigger).not.toBeDisabled()
    expect(trigger).toHaveAttribute('aria-haspopup', 'dialog')
    expect(trigger.className).toMatch(/opacity-50/)
    expect(trigger.querySelector('svg')).toBeTruthy()
  })

  it('opens a DaisyUI WIP modal; does not drive a machine', () => {
    render(<ComputerControlStub />)

    fireEvent.click(screen.getByRole('button', { name: 'Computer control' }))

    const dialog = screen.getByRole('dialog', { hidden: true })
    expect(dialog).toHaveClass('modal-open')
    expect(dialog).toHaveTextContent('WIP')
    expect(dialog).toHaveTextContent(COMPUTER_CONTROL_WIP_COPY)
    expect(dialog).toHaveTextContent(/OMB or Rakazo remote/i)

    expect(dialog.textContent).not.toMatch(/E2B|xdotool|CDP|CUA|sandbox|enable/i)
    expect(
      screen.queryByRole('checkbox', { hidden: true }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('switch', { hidden: true }),
    ).not.toBeInTheDocument()
  })

  it('closes the modal from the Close action', () => {
    render(<ComputerControlStub />)

    fireEvent.click(screen.getByRole('button', { name: 'Computer control' }))
    expect(screen.getByRole('dialog', { hidden: true })).toHaveClass('modal-open')

    fireEvent.click(screen.getByRole('button', { name: 'Close', exact: true }))
    expect(screen.getByRole('dialog', { hidden: true })).not.toHaveClass(
      'modal-open',
    )
  })
})
