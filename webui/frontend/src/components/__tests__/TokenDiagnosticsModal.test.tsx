import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TokenDiagnosticsModal } from '../TokenDiagnosticsModal'

describe('TokenDiagnosticsModal (REQ-115)', () => {
  it('does not have modal-open class when closed', () => {
    render(
      <TokenDiagnosticsModal
        isOpen={false}
        onClose={vi.fn()}
        tokenCount={500}
      />
    )
    const dialog = screen.getByRole('dialog', { hidden: true })
    expect(dialog).not.toHaveClass('modal-open')
  })

  it('renders all honest diagnostics metrics when open', () => {
    const onClose = vi.fn()
    render(
      <TokenDiagnosticsModal
        isOpen={true}
        onClose={onClose}
        agentName="Stewie"
        conversationId="conv-test-123"
        tokenCount={4200}
        inputTokens={1500}
        outputTokens={2700}
        compactsCount={2}
        toolCallsCount={5}
        messageCount={8}
        userMessageCount={4}
        assistantMessageCount={4}
      />
    )

    expect(screen.getByTestId('token-diagnostics-modal')).toBeInTheDocument()
    expect(screen.getByText('Session Token Diagnostics')).toBeInTheDocument()
    expect(screen.getByText(/Current Agent:/i)).toBeInTheDocument()
    expect(screen.getByTestId('diag-current-agent')).toHaveTextContent('Stewie')
    expect(screen.getByTestId('diag-session-id')).toHaveTextContent('conv-test-123')
    expect(screen.getByTestId('diag-context-usage')).toHaveTextContent('4.2k / 128k tok')

    // Breakdown metrics
    expect(screen.getByTestId('diag-input-tokens')).toHaveTextContent('1.5k')
    expect(screen.getByTestId('diag-output-tokens')).toHaveTextContent('2.7k')
    expect(screen.getByTestId('diag-compacts-count')).toHaveTextContent('2')
    expect(screen.getByTestId('diag-tool-calls')).toHaveTextContent('5')
    expect(screen.getByTestId('diag-message-count')).toHaveTextContent('8')
    expect(screen.getByTestId('diag-estimated-cost')).toHaveTextContent('—')
  })

  it('updates Current Agent dynamically when agent changes without sticky name', () => {
    const { rerender } = render(
      <TokenDiagnosticsModal
        isOpen={true}
        onClose={vi.fn()}
        agentName="FirstAgent"
        conversationId="conv-test-123"
        tokenCount={100}
      />
    )

    expect(screen.getByTestId('diag-current-agent')).toHaveTextContent('FirstAgent')

    rerender(
      <TokenDiagnosticsModal
        isOpen={true}
        onClose={vi.fn()}
        agentName="SwitchedAgent"
        conversationId="conv-test-123"
        tokenCount={120}
      />
    )

    expect(screen.getByTestId('diag-current-agent')).toHaveTextContent('SwitchedAgent')
    expect(screen.queryByText('FirstAgent')).not.toBeInTheDocument()
  })

  it('handles empty/unknown fields with honest placeholders', () => {
    render(
      <TokenDiagnosticsModal
        isOpen={true}
        onClose={vi.fn()}
        tokenCount={0}
      />
    )

    expect(screen.getByTestId('diag-session-id')).toHaveTextContent('—')
    expect(screen.getByTestId('diag-context-usage')).toHaveTextContent('0 / 128k tok (0%)')
    expect(screen.getByTestId('diag-compacts-count')).toHaveTextContent('0')
    expect(screen.getByTestId('diag-tool-calls')).toHaveTextContent('0')
    expect(screen.getByTestId('diag-message-count')).toHaveTextContent('0')
    expect(screen.getByTestId('diag-estimated-cost')).toHaveTextContent('—')
  })

  it('triggers onClose when close button or X button is clicked', () => {
    const onClose = vi.fn()
    render(
      <TokenDiagnosticsModal
        isOpen={true}
        onClose={onClose}
        tokenCount={100}
      />
    )

    const xButton = screen.getByRole('button', { name: 'Close diagnostics' })
    fireEvent.click(xButton)
    expect(onClose).toHaveBeenCalledTimes(1)

    const closeBottomButton = screen.getByRole('button', { name: 'Close' })
    fireEvent.click(closeBottomButton)
    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it('triggers onClose when cancel event or backdrop is clicked', () => {
    const onClose = vi.fn()
    render(
      <TokenDiagnosticsModal
        isOpen={true}
        onClose={onClose}
        tokenCount={100}
      />
    )

    const dialog = screen.getByRole('dialog')
    fireEvent(dialog, new Event('cancel'))
    expect(onClose).toHaveBeenCalledTimes(1)

    const backdropButton = screen.getByRole('button', { name: 'Close modal', hidden: true })
    fireEvent.click(backdropButton)
    expect(onClose).toHaveBeenCalledTimes(2)
  })
})
