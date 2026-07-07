import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from '../Button'

describe('Button loading state (DaisyUI 5)', () => {
  it('renders a visible spinner element when loading', () => {
    render(<Button loading>Save</Button>)
    // DaisyUI 5 needs an explicit loading-spinner span (the bare `loading` btn
    // class no longer renders one).
    const srText = screen.getByText('Loading');
    expect(srText).toBeInTheDocument();
    // Use data-testid or dom traversal instead of innerHTML to adhere to testing standards.
    const spinner = screen.getByTestId('button-loading-spinner');
    expect(spinner).toHaveClass('loading-spinner');
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
    const srText = screen.queryByText('Loading');
    expect(srText).toBeNull();
  })
})
