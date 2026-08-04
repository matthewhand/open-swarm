import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from '../Button'

describe('Button loading state (DaisyUI 5)', () => {
  it('renders a visible spinner element when loading', () => {
    const { container } = render(<Button loading>Save</Button>)
    // DaisyUI 5 needs an explicit loading-spinner span (the bare `loading` btn
    // class no longer renders one). The spinner uses aria-hidden="true" in Button.tsx,
    // so we can test its presence by asserting on the structural element.
    // eslint-disable-next-line testing-library/no-container, testing-library/no-node-access
    const spinner = container.querySelector('.loading.loading-spinner')
    expect(spinner).not.toBeNull()
  })

  it('does not add the deprecated bare `loading` class to the button', () => {
    render(<Button loading>Save</Button>)
    const btn = screen.getByRole('button')
    expect(btn.classList.contains('loading')).toBe(false)
  })

  it('marks the button busy + disabled and exposes SR text while loading', () => {
    render(<Button loading>Save</Button>)
    const btn = screen.getByRole('button')
    expect(btn).toBeDisabled()
    expect(btn).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByText('Loading')).toHaveClass('sr-only')
  })

  it('renders no spinner when not loading', () => {
    const { container } = render(<Button>Save</Button>)
    // eslint-disable-next-line testing-library/no-container, testing-library/no-node-access
    expect(container.querySelector('.loading-spinner')).toBeNull()
  })
})
