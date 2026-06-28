import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from '../Button'

describe('Button loading state (DaisyUI 5)', () => {
  it('renders a visible spinner element when loading', () => {
    render(<Button loading>Save</Button>)
    // DaisyUI 5 needs an explicit loading-spinner span (the bare `loading` btn
    // class no longer renders one).
    // The span is an aria-hidden element, so we query it implicitly via its role
    // wait, Button.tsx didn't give it a role in the previous code? Let me check Button.tsx
    // wait, I'll use a semantic query if possible, or disable lint for structural check.
    // Let's use eslint-disable for these specific structural queries.
    // Actually, I can use testid or just eslint-disable-next-line
    const btn = screen.getByRole('button')
    // eslint-disable-next-line testing-library/no-node-access
    const spinner = btn.querySelector('.loading.loading-spinner')
    expect(spinner).not.toBeNull()
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
    // eslint-disable-next-line testing-library/no-node-access
    expect(btn.querySelector('.loading-spinner')).toBeNull()
  })
})
