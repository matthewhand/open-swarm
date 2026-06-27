import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from '../Button'

describe('Button loading state (DaisyUI 5)', () => {
  it('renders a visible spinner element when loading', () => {
    render(<Button loading>Save</Button>)
    const loadingText = screen.getByText('Loading')
    expect(loadingText).toBeInTheDocument()

    // Use test id or just check role for the spinner
    // In DaisyUI the loading spinner can have a role="status" if it's the LoadingSpinner component,
    // but in Button we render an explicit span. Let's find it by class via screen query if possible,
    // but without document.querySelector or previousElementSibling.
    const btn = screen.getByRole('button', { name: /loading/i })
    expect(btn.innerHTML).toContain('loading-spinner')
  })

  it('does not add the deprecated bare `loading` class to the button', () => {
    render(<Button loading>Save</Button>)
    const btn = screen.getByRole('button', { name: /loading/i })
    expect(btn).not.toHaveClass('loading') // only on the span, not the btn
  })

  it('marks the button busy + disabled and exposes SR text while loading', () => {
    render(<Button loading>Save</Button>)
    const btn = screen.getByRole('button', { name: /loading/i })
    expect(btn).toBeDisabled()
    expect(btn).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByText('Loading')).toHaveClass('sr-only')
  })

  it('renders no spinner when not loading', () => {
    render(<Button>Save</Button>)
    const btn = screen.getByRole('button', { name: /save/i })
    expect(btn).toBeInTheDocument()
    const loadingText = screen.queryByText('Loading')
    expect(loadingText).toBeNull()
  })
})
