import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ToolCallPopup, ToolStatusBadge } from '../ToolCallPopup'
import type { ToolCallState } from '../../lib/safety'

function tool(status: ToolCallState['status'], extra: Partial<ToolCallState> = {}): ToolCallState {
  return { id: 't1', name: 'write_file', status, ...extra }
}

describe('ToolStatusBadge', () => {
  it('renders blue running, green allowed/done, red denied/error', () => {
    const { rerender } = render(<ToolStatusBadge status="running" />)
    const badge = screen.getByTestId('tool-status-badge')
    expect(badge).toHaveAttribute('data-status', 'running')
    expect(badge.closest('.badge')).toHaveClass('badge-info')
    expect(badge.closest('.os-tool-badge-running')).toBeTruthy()

    rerender(<ToolStatusBadge status="allowed" />)
    expect(screen.getByTestId('tool-status-badge').closest('.badge')).toHaveClass('badge-success')

    rerender(<ToolStatusBadge status="done" />)
    expect(screen.getByTestId('tool-status-badge').closest('.badge')).toHaveClass('badge-success')

    rerender(<ToolStatusBadge status="denied" />)
    expect(screen.getByTestId('tool-status-badge').closest('.badge')).toHaveClass('badge-error')

    rerender(<ToolStatusBadge status="error" />)
    expect(screen.getByTestId('tool-status-badge').closest('.badge')).toHaveClass('badge-error')
  })
})

describe('ToolCallPopup', () => {
  it('prompts Allow once / Always allow / Deny when Safety is concerned', () => {
    const onDecision = vi.fn()
    render(<ToolCallPopup tool={tool('running', { needsApproval: true })} onDecision={onDecision} />)
    expect(screen.getByRole('dialog', { name: 'Safety approval' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Allow once' }))
    fireEvent.click(screen.getByRole('button', { name: 'Always allow' }))
    fireEvent.click(screen.getByRole('button', { name: 'Deny' }))
    expect(onDecision).toHaveBeenCalledWith('allow')
    expect(onDecision).toHaveBeenCalledWith('always')
    expect(onDecision).toHaveBeenCalledWith('deny')
  })

  it('does not prompt when the call is unconcerned', () => {
    render(<ToolCallPopup tool={tool('running', { needsApproval: false })} />)
    expect(screen.queryByRole('dialog', { name: 'Safety approval' })).not.toBeInTheDocument()
  })
})
