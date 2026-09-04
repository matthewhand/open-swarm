import { afterEach, describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import KeybindingTips from '../KeybindingTips'
import { KEYBINDING_TIPS_STORAGE_KEY } from '../../lib/keybindingTips'

describe('KeybindingTips', () => {
  afterEach(() => {
    localStorage.removeItem(KEYBINDING_TIPS_STORAGE_KEY)
  })

  it('renders Search, Pins, and Clear tips then persists dismiss', () => {
    render(<KeybindingTips />)
    const tips = screen.getByTestId('first-load-tips')
    expect(tips).toHaveTextContent('Search')
    expect(tips).toHaveTextContent('Pins')
    expect(tips).toHaveTextContent('Clear')
    expect(tips.className).toContain('os-keybinding-tips')
    expect(tips.className).not.toContain('alert')

    fireEvent.click(screen.getByRole('button', { name: 'Dismiss tips' }))
    expect(screen.queryByTestId('first-load-tips')).not.toBeInTheDocument()
    expect(localStorage.getItem(KEYBINDING_TIPS_STORAGE_KEY)).toBe('1')
  })

  it('stays hidden when dismiss is already persisted', () => {
    localStorage.setItem(KEYBINDING_TIPS_STORAGE_KEY, '1')
    render(<KeybindingTips />)
    expect(screen.queryByTestId('first-load-tips')).not.toBeInTheDocument()
  })
})
