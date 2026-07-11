import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from '../Button'

describe('Button loading state (DaisyUI 5)', () => {
  it('renders a visible spinner element when loading', () => {
    render(<Button loading>Save</Button>)
    // The button renders a span with aria-hidden="true" containing the DaisyUI class
    const btn = screen.getByRole('button')
    // We cannot use getByRole for aria-hidden elements easily, so we use data-testid or dom traversal.
    // Testing library lint rule discourages this but the element literally has aria-hidden=true and no role.
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
    expect(btn.querySelector('.loading.loading-spinner')).toBeNull()
  })
})
