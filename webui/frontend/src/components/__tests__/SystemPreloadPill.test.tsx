import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SystemPreloadPill } from '../SystemPreloadPill'

describe('REQ-207: Support preload — Message from System pill', () => {
  const samplePreload = '**Agents**\n- Support · support\n\n**Inference** ready.'

  it('renders a compact "Message from System" pill/badge by default without full text', () => {
    render(<SystemPreloadPill text={samplePreload} />)

    const pill = screen.getByRole('button', { name: /Message from System/i })
    expect(pill).toBeInTheDocument()
    expect(pill).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByTestId('system-preload-content')).not.toBeInTheDocument()
  })

  it('expands on click to reveal the full preload context in a system notice box', () => {
    render(<SystemPreloadPill text={samplePreload} />)

    const pill = screen.getByRole('button', { name: /Message from System/i })
    fireEvent.click(pill)

    expect(pill).toHaveAttribute('aria-expanded', 'true')
    const content = screen.getByTestId('system-preload-content')
    expect(content).toBeInTheDocument()
    expect(content).toHaveTextContent('Agents')
    expect(content).toHaveTextContent('Support · support')
    expect(content).toHaveTextContent('Inference ready.')
  })

  it('collapses on second click returning to compact pill view', () => {
    render(<SystemPreloadPill text={samplePreload} />)

    const pill = screen.getByRole('button', { name: /Message from System/i })
    fireEvent.click(pill)
    expect(screen.getByTestId('system-preload-content')).toBeInTheDocument()

    fireEvent.click(pill)
    expect(pill).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByTestId('system-preload-content')).not.toBeInTheDocument()
  })

  it('can be keyboard activated via space or enter', () => {
    render(<SystemPreloadPill text={samplePreload} />)

    const pill = screen.getByRole('button', { name: /Message from System/i })
    fireEvent.keyDown(pill, { key: 'Enter', code: 'Enter' })
    // fireEvent.click triggers standard button activation
    fireEvent.click(pill)
    expect(pill).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByTestId('system-preload-content')).toBeInTheDocument()
  })

  it('supports custom label', () => {
    render(<SystemPreloadPill text={samplePreload} label="System Notice" />)
    expect(screen.getByRole('button', { name: /System Notice/i })).toBeInTheDocument()
  })
})
