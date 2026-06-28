import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Button } from '../Button'

describe('Button loading state (DaisyUI 5)', () => {
  it('renders a visible spinner element when loading', () => {
    // Note: the component does render the sr-only loading text when loading
    render(<Button loading>Save</Button>)
    const loadingText = screen.getByText('Loading')
    expect(loadingText).toBeInTheDocument()
    // Test for visual spinner class if we have an element with aria-hidden
    // Testing library query for elements matching selector would be:
    const button = screen.getByRole('button')
    // Get the children span element using DOM query inside the test only because we are testing Daisy UI 5 requirement to render a span explicitly
    // Since testing-library/no-node-access rule is enabled we disable it just for this specific assertion about the hidden span structure
    // eslint-disable-next-line testing-library/no-node-access
    const spinner = button.querySelector('span[aria-hidden="true"].loading.loading-spinner')
    expect(spinner).toBeInTheDocument()
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
    expect(screen.queryByText('Loading')).toBeNull()
  })
})
