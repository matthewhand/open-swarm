import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from '../Button'

describe('Button loading state (DaisyUI 5)', () => {
  it('renders a visible spinner element when loading', () => {
    // We cannot use getByRole for aria-hidden="true" elements because they are
    // hidden from the accessibility tree, which is why we must query the DOM structure
    // eslint-disable-next-line testing-library/no-node-access, testing-library/no-container
    const { container } = render(<Button loading>Save</Button>)
    // eslint-disable-next-line testing-library/no-node-access, testing-library/no-container
    const spinner = container.querySelector('.loading.loading-spinner')
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

    // Check that there's an element with role="status" acting as the live region
    const statusEl = screen.getByRole('status')
    expect(statusEl).toHaveTextContent('Loading')
    expect(statusEl).toHaveClass('sr-only')
  })

  it('renders no spinner when not loading', () => {
    // eslint-disable-next-line testing-library/no-node-access, testing-library/no-container
    const { container } = render(<Button>Save</Button>)
    // eslint-disable-next-line testing-library/no-node-access, testing-library/no-container
    expect(container.querySelector('.loading-spinner')).toBeNull()
  })
})
