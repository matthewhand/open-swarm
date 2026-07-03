import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from '../Button'

describe('Button loading state (DaisyUI 5)', () => {
  it('renders a visible spinner element when loading', () => {
    render(<Button loading>Save</Button>)
    // DaisyUI 5 needs an explicit loading-spinner span (the bare `loading` btn
    // class no longer renders one).
    // In DaisyUI, loading spinners are typically rendered with aria-hidden="true"
    // The memory says: "Frontend tests for DaisyUI components (e.g., loading states in Buttons) should verify accessibility using screen reader text (e.g., `screen.getByText('Loading')`) rather than querying DOM structure directly, as loading spinners are often rendered with `aria-hidden="true"`."
    const srText = screen.getByText('Loading')
    expect(srText).toBeInTheDocument()
    expect(srText).toHaveClass('sr-only')
  })

  it('does not add the deprecated bare `loading` class to the button', () => {
    render(<Button loading>Save</Button>)
    const btn = screen.getByRole('button')
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
    render(<Button>Save</Button>)
    const loadingText = screen.queryByText('Loading')
    expect(loadingText).toBeNull()
  })
})
