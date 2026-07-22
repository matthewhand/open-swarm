import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from '../Button'

describe('Button loading state (DaisyUI 5)', () => {
  it('renders a visible spinner element when loading', () => {
    render(<Button loading>Save</Button>)
    // In DaisyUI 5, the loading state generates a spinner with role status or is aria-hidden
    // We check via ARIA text first, fallback to DOM structure if we must (or adjust component).
    // The component includes <span className="sr-only">Loading</span>
    expect(screen.getByText('Loading')).toBeInTheDocument()

    // Test the button state instead of querying inner span classes
    const btn = screen.getByRole('button')
    expect(btn).toHaveAttribute('aria-busy', 'true')
  })

  it('does not add the deprecated bare `loading` class to the button', () => {
    render(<Button loading>Save</Button>)
    const btn = screen.getByRole('button')
    const classes = btn.className.split(/\s+/)
    expect(classes).not.toContain('loading') // only on the span, not the btn
  })

  it('marks the button busy + disabled and exposes SR text while loading', () => {
    render(<Button loading>Save</Button>)
    const btn = screen.getByRole('button')
    expect(btn).toBeDisabled()
    expect(btn).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByText('Loading')).toHaveClass('sr-only')
  })

  it('renders no spinner when not loading', () => {
    render(<Button>Save</Button>)
    const btn = screen.getByRole('button')
    expect(btn).toHaveAttribute('aria-busy', 'false')
    expect(screen.queryByText('Loading')).not.toBeInTheDocument()
  })
})
