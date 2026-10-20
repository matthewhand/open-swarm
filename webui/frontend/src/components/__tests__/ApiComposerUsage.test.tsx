import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ApiComposerUsage } from '../ApiComposerUsage'
import type { ContextUsage } from '../../lib/contextUsage'

const sample: ContextUsage = {
  type: 'context_usage', conversation_id: 'demo', agent_id: 'support',
  tokens: 16000, window: 128000, pct: 13, last_output: 320, estimate: true,
  breakdown: { messages: 12000, summaries: 2000, system: 1500, tools: 500 },
}
function expand() { fireEvent.click(screen.getByRole('button', { name: 'Context window usage' })) }

describe('API composer usage disclosure', () => {
  it('shows readable context tokens and expands with labelled reply usage', () => {
    render(<ApiComposerUsage usage={sample} />)
    expect(screen.getByRole('button', { name: 'Context window usage' })).toHaveTextContent('Context16k tokens')
    expect(screen.queryByRole('region', { name: 'Token usage details' })).toBeNull()
    expand()
    expect(screen.getByRole('region', { name: 'Token usage details' })).toHaveTextContent('Context used16k tokensLast reply320 tokens')
    expect(screen.getByText('Estimated')).toBeVisible()
    expect(screen.getByText(/estimated from text length/)).toBeVisible()
  })

  it('uses the real capacity and an accessible, bounded meter', () => {
    render(<ApiComposerUsage usage={sample} />)
    expand()
    const bar = screen.getByRole('progressbar', { name: 'Context capacity used' })
    expect(bar).toHaveAttribute('aria-valuemax', '128000')
    expect(bar).toHaveAttribute('aria-valuenow', '16000')
    expect(screen.getByText('12.5% of context used')).toBeVisible()
  })

  it('does not invent a capacity or percentage when the window is unknown', () => {
    render(<ApiComposerUsage usage={{ ...sample, window: null, pct: null }} />)
    expand()
    expect(screen.queryByRole('progressbar')).toBeNull()
    expect(screen.getByText('Context capacity is not reported by this model.')).toBeVisible()
    expect(screen.getByRole('region').parentElement).toHaveAttribute('data-level', 'none')
  })

  it('handles unavailable usage without presenting a zero estimate', () => {
    render(<ApiComposerUsage usage={null} />)
    expect(screen.getByRole('button', { name: 'Context window usage' })).toHaveTextContent('Not yet measured')
    expand()
    expect(screen.getByText(/after your conversation is measured/)).toBeVisible()
    expect(screen.queryByRole('progressbar')).toBeNull()
  })

  it('clamps over-capacity graphics but reports the actual proportion', () => {
    render(<ApiComposerUsage usage={{ ...sample, tokens: 256000 }} />)
    expand()
    const bar = screen.getByRole('progressbar')
    expect(bar).toHaveAttribute('aria-valuenow', '128000')
    expect(bar.firstElementChild).toHaveStyle({ width: '100%' })
    expect(screen.getByText('200% of context used')).toBeVisible()
  })

  it('keeps advanced diagnostics accessible without submitting the composer', () => {
    const details = vi.fn()
    const submit = vi.fn(event => event.preventDefault())
    render(<form onSubmit={submit}><ApiComposerUsage usage={sample} onOpenDetail={details} /></form>)
    expand()
    fireEvent.click(screen.getByRole('button', { name: 'More details' }))
    expect(details).toHaveBeenCalledOnce()
    expect(submit).not.toHaveBeenCalled()
  })

  it('closes with Escape and returns focus to the disclosure', () => {
    render(<ApiComposerUsage usage={sample} />)
    expand()
    fireEvent.keyDown(screen.getByRole('region'), { key: 'Escape' })
    expect(screen.queryByRole('region')).toBeNull()
    expect(screen.getByRole('button', { name: 'Context window usage' })).toHaveFocus()
  })

  it('updates a visible panel with new usage and distinguishes reported counts', () => {
    const { rerender } = render(<ApiComposerUsage usage={sample} />)
    expand()
    rerender(<ApiComposerUsage usage={{ ...sample, tokens: 8000, estimate: false, last_output: 0 }} />)
    expect(screen.getByText('Reported')).toBeVisible()
    expect(screen.getByText('6.3% of context used')).toBeVisible()
    expect(screen.getByText('Not available yet')).toBeVisible()
    expect(screen.queryByText(/estimated from text length/)).toBeNull()
  })
})
