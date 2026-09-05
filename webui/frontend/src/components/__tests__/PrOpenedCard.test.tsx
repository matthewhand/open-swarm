import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { PrOpenedCard } from '../PrOpenedCard'
import type { PrOpenedEvent } from '../../lib/prOpened'

const GH = 'https://github.com/matthewhand/open-swarm/pull/416'

function event(extra: Partial<PrOpenedEvent> = {}): PrOpenedEvent {
  return {
    type: 'pr_opened',
    url: GH,
    number: 416,
    title: 'REQ-71: PR-opened card',
    ...extra,
  }
}

describe('PrOpenedCard', () => {
  it('renders DaisyUI chrome with View PR and omits missing optionals', () => {
    const { container } = render(
      <PrOpenedCard event={event()} currentAgentId="codey" currentConversationId="conv-1" />,
    )
    const card = screen.getByTestId('pr-opened-card')
    expect(card).toHaveClass('card')
    expect(screen.getByTestId('pr-opened-title')).toHaveTextContent('REQ-71: PR-opened card')
    expect(screen.getByTestId('pr-opened-number')).toHaveTextContent('PR #416')
    expect(screen.queryByTestId('pr-opened-branch')).not.toBeInTheDocument()
    expect(screen.queryByTestId('pr-opened-stats')).not.toBeInTheDocument()
    const view = screen.getByTestId('pr-opened-view')
    expect(view).toHaveAttribute('href', GH)
    expect(view).toHaveAttribute('target', '_blank')
    expect(view).toHaveTextContent('View PR')
    expect(screen.queryByTestId('pr-opened-jump')).not.toBeInTheDocument()
    expect(container.textContent).not.toMatch(/Open in Cursor/i)
    expect(container.textContent).not.toMatch(/Cursor/)
  })

  it('shows optional branch, status, and +N/-M only when supplied', () => {
    render(
      <PrOpenedCard
        event={event({ branch: 'feat/card', additions: 8, deletions: 2, status: 'Done' })}
        currentAgentId="codey"
      />,
    )
    expect(screen.getByTestId('pr-opened-branch')).toHaveTextContent('feat/card')
    expect(screen.getByTestId('pr-opened-stats')).toHaveTextContent('+8')
    expect(screen.getByTestId('pr-opened-stats')).toHaveTextContent('-2')
    expect(screen.getByText('Done')).toBeInTheDocument()
  })

  it('same agent same thread: View PR only — zero jump controls', () => {
    render(
      <PrOpenedCard
        event={event({ opener: { agentId: 'codey', name: 'Codey', conversationId: 'conv-1' } })}
        currentAgentId="codey"
        currentConversationId="conv-1"
      />,
    )
    expect(screen.getByTestId('pr-opened-view')).toBeInTheDocument()
    expect(screen.queryByTestId('pr-opened-jump')).not.toBeInTheDocument()
  })

  it('different opener: avatar+name jump selects that agent, not Open in Cursor', () => {
    const onJump = vi.fn()
    render(
      <PrOpenedCard
        event={event({ opener: { agentId: 'codey', name: 'Codey', conversationId: 'conv-codey' } })}
        currentAgentId="support"
        currentConversationId="conv-support"
        openerName="Codey"
        onJumpToOpener={onJump}
      />,
    )
    const jump = screen.getByTestId('pr-opened-jump')
    expect(jump).toHaveTextContent('Codey')
    expect(jump).not.toHaveTextContent('Open in Cursor')
    expect(jump.querySelector('[data-agent-avatar]')).toBeTruthy()
    fireEvent.click(jump)
    expect(onJump).toHaveBeenCalledWith({
      agentId: 'codey',
      name: 'Codey',
      conversationId: 'conv-codey',
    })
  })

  it('does not put a quoted title into aria-label (title stays React text)', () => {
    const nasty = '"><img src=x onerror=alert(1)>'
    render(<PrOpenedCard event={event({ title: nasty })} currentAgentId="codey" />)
    const card = screen.getByTestId('pr-opened-card')
    expect(card).toHaveAttribute('aria-label', 'Pull request #416')
    expect(card.getAttribute('aria-label')).not.toContain('<')
    expect(card.querySelector('img[src="x"]')).toBeNull()
    expect(screen.getByTestId('pr-opened-title')).toHaveTextContent(nasty)
  })

  it('malformed or missing PR URL: no fake View PR', () => {
    const { rerender } = render(
      <PrOpenedCard event={event({ url: 'https://example.com/pull/1' })} currentAgentId="codey" />,
    )
    expect(screen.queryByTestId('pr-opened-view')).not.toBeInTheDocument()
    rerender(<PrOpenedCard event={event({ url: undefined })} currentAgentId="codey" />)
    expect(screen.queryByTestId('pr-opened-view')).not.toBeInTheDocument()
    rerender(
      <PrOpenedCard event={event({ url: 'http://127.0.0.1:8001/pull/9' })} currentAgentId="codey" />,
    )
    expect(screen.queryByTestId('pr-opened-view')).not.toBeInTheDocument()
  })
})
