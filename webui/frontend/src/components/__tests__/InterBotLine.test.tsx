import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import InterBotLine from '../InterBotLine'
import { hopFromAssistantName, type InterBotHop, type InterBotLine as InterBotLineData } from '../../lib/interBot'

function hop(id: string, name: string): InterBotHop {
  return hopFromAssistantName(id, name, false)
}

function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="interbot-loc">{`${loc.pathname}${loc.search}`}</div>
}

function renderLine(line: InterBotLineData, onSelectAgent?: (hop: InterBotHop) => void) {
  return render(
    <MemoryRouter initialEntries={['/chat?blueprint=support']}>
      <Routes>
        <Route
          path="/chat"
          element={
            <>
              <InterBotLine line={line} onSelectAgent={onSelectAgent} />
              <LocationProbe />
            </>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('InterBotLine multi-hop picker', () => {
  const multi: InterBotLineData = {
    kind: 'multi',
    hops: [hop('1', 'HASS'), hop('2', 'Codey'), hop('3', 'Stewie')],
  }

  it('renders the stack and N Bots trigger without a menu until clicked', () => {
    renderLine(multi)
    expect(screen.getByText('Messaged')).toBeInTheDocument()
    expect(screen.getByTestId('os-interbot-count')).toHaveTextContent('3 Bots')
    expect(screen.getByTestId('os-interbot-multi-trigger')).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    expect(screen.queryByText(/Cursor/i)).not.toBeInTheDocument()
  })

  it('opens a DaisyUI menu of every bot from the stack or N Bots label', () => {
    renderLine(multi)
    fireEvent.click(screen.getByTestId('os-interbot-multi-trigger'))
    const menu = screen.getByRole('menu', { name: 'Messaged 3 Bots' })
    expect(menu).toHaveClass('dropdown-content')
    expect(menu).toHaveClass('menu')
    expect(within(menu).getByRole('menuitem', { name: 'HASS' })).toBeInTheDocument()
    expect(within(menu).getByRole('menuitem', { name: 'Codey' })).toBeInTheDocument()
    expect(within(menu).getByRole('menuitem', { name: 'Stewie' })).toBeInTheDocument()
    expect(within(menu).getAllByRole('menuitem')).toHaveLength(3)
  })

  it('navigates to /chat?blueprint= when a menu row is chosen', () => {
    const onSelect = vi.fn()
    renderLine(multi, onSelect)
    fireEvent.click(screen.getByTestId('os-interbot-multi-trigger'))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Codey' }))
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ name: 'Codey', agentId: 'codey' }))
    expect(screen.getByTestId('interbot-loc')).toHaveTextContent('/chat?blueprint=codey')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('opens with Enter or Space and closes with Escape', () => {
    renderLine(multi)
    const trigger = screen.getByTestId('os-interbot-multi-trigger')
    trigger.focus()
    fireEvent.keyDown(trigger, { key: 'Enter' })
    expect(screen.getByRole('menu')).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()

    fireEvent.keyDown(trigger, { key: ' ' })
    expect(screen.getByRole('menu')).toBeInTheDocument()
    fireEvent.keyDown(trigger, { key: 'Escape' })
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('moves the active menu row with arrow keys', () => {
    renderLine(multi)
    fireEvent.click(screen.getByTestId('os-interbot-multi-trigger'))
    const menu = screen.getByRole('menu')
    expect(screen.getByRole('menuitem', { name: 'HASS' })).toHaveClass('active')
    fireEvent.keyDown(menu, { key: 'ArrowDown' })
    expect(screen.getByRole('menuitem', { name: 'Codey' })).toHaveClass('active')
    fireEvent.keyDown(menu, { key: 'ArrowDown' })
    expect(screen.getByRole('menuitem', { name: 'Stewie' })).toHaveClass('active')
    fireEvent.keyDown(menu, { key: 'ArrowUp' })
    expect(screen.getByRole('menuitem', { name: 'Codey' })).toHaveClass('active')
  })
})

describe('InterBotLine single-hop', () => {
  it('jumps directly to the named agent without a menu', () => {
    const onSelect = vi.fn()
    renderLine({ kind: 'single', hop: hop('1', 'HASS') }, onSelect)
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    const jump = screen.getByTestId('os-interbot-single-jump')
    expect(jump).toHaveAttribute('href', '/chat?blueprint=hass')
    fireEvent.click(jump)
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ name: 'HASS', agentId: 'hass' }))
    expect(screen.getByTestId('interbot-loc')).toHaveTextContent('/chat?blueprint=hass')
    expect(screen.queryByText(/Cursor/i)).not.toBeInTheDocument()
  })
})

describe('InterBotLine progress', () => {
  it('keeps pending hops as dots only', () => {
    renderLine({ kind: 'progress' })
    expect(document.querySelector('.os-interbot-line[data-pending="true"]')).toBeTruthy()
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    expect(screen.queryByText(/Bots/i)).not.toBeInTheDocument()
  })
})
