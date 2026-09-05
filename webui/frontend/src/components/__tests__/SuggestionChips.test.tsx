import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SuggestionChips } from '../SuggestionChips'

describe('SuggestionChips', () => {
  it('renders DaisyUI chips and sends the exact string', () => {
    const onChoose = vi.fn()
    render(<SuggestionChips chips={['Ask about setup', 'Try a demo']} onChoose={onChoose} />)
    const row = screen.getByTestId('suggestion-chips')
    expect(row).toHaveAttribute('role', 'group')
    const buttons = screen.getAllByTestId('suggestion-chip')
    expect(buttons[0]).toHaveClass('btn')
    expect(buttons[0]).toHaveAttribute('data-suggestion-chip', 'Ask about setup')
    fireEvent.click(buttons[0]!)
    expect(onChoose).toHaveBeenCalledWith('Ask about setup')
  })

  it('does not fire while disabled', () => {
    const onChoose = vi.fn()
    render(<SuggestionChips chips={['Later']} disabled onChoose={onChoose} />)
    fireEvent.click(screen.getByTestId('suggestion-chip'))
    expect(onChoose).not.toHaveBeenCalled()
  })
})
