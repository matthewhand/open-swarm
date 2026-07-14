import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from '../Button'

describe('Button loading state (DaisyUI 5)', () => {
  it('renders a visible spinner element when loading', () => {
    render(<Button loading data-testid="test-btn">Save</Button>)
    // DaisyUI 5 needs an explicit loading-spinner span (the bare `loading` btn
    // class no longer renders one).
    const btn = screen.getByTestId('test-btn')
    // We expect the button to have a span with aria-hidden="true" acting as the spinner
    expect(screen.getAllByRole('button')[0]).toBeInTheDocument()
    // It's better to just check the DOM string if we can't use node access
    expect(btn.innerHTML).toContain('loading-spinner')
  })

  it('does not add the deprecated bare `loading` class to the button', () => {
    render(<Button loading data-testid="test-btn">Save</Button>)
    const btn = screen.getByTestId('test-btn')
    expect(btn).not.toHaveClass('loading')
  })

  it('marks the button busy + disabled and exposes SR text while loading', () => {
    render(<Button loading>Save</Button>)
    const btn = screen.getByRole('button')
    expect(btn).toBeDisabled()
    expect(btn).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByText('Loading')).toHaveClass('sr-only')
  })

  it('renders no spinner when not loading', () => {
    render(<Button data-testid="test-btn">Save</Button>)
    const btn = screen.getByTestId('test-btn')
    expect(btn.innerHTML).not.toContain('loading-spinner')
  })
})
