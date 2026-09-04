import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import SessionPicker from '../SessionPicker'
import type { AgentSession } from '../../lib/scaleOutSessions'

function session(
  id: string,
  title: string,
  snippet: string,
  status: AgentSession['status'],
  startedAt: number,
): AgentSession {
  return {
    id,
    agentId: 'codey',
    title,
    snippet,
    status,
    startedAt,
    updatedAt: startedAt,
  }
}

const FIXTURE: AgentSession[] = [
  session('run-1', 'Task one', 'alpha work', 'running', 4_000),
  session('run-2', 'Task two', 'bravo work', 'running', 3_000),
  session('run-3', 'Task three', 'charlie work', 'running', 2_000),
  session('run-4', 'Task four', 'delta work', 'running', 1_000),
  session('fin-1', 'Old job', 'finished fixture', 'finished', 500),
]

function renderPicker(onSelect = vi.fn(), onClose = vi.fn()) {
  return {
    onSelect,
    onClose,
    ...render(
      <SessionPicker
        open
        agentName="Codey"
        sessions={FIXTURE}
        onClose={onClose}
        onSelect={onSelect}
      />,
    ),
  }
}

describe('SessionPicker', () => {
  it('lists four running sessions plus a finished fixture and filters by snippet', () => {
    renderPicker()

    const dialog = screen.getByRole('dialog', { name: 'Codey sessions' })
    const options = within(dialog).getAllByRole('option')
    expect(options).toHaveLength(5)
    expect(options.map((row) => row.getAttribute('data-session-id'))).toEqual([
      'run-1',
      'run-2',
      'run-3',
      'run-4',
      'fin-1',
    ])
    expect(within(dialog).getByText('finished fixture', { exact: false })).toBeInTheDocument()

    fireEvent.change(screen.getByRole('combobox', { name: /Filter Codey sessions/i }), {
      target: { value: 'finished' },
    })
    const narrowed = within(dialog).getAllByRole('option')
    expect(narrowed).toHaveLength(1)
    expect(narrowed[0]).toHaveAttribute('data-session-id', 'fin-1')
  })

  it('selects the clicked session id', () => {
    const { onSelect, onClose } = renderPicker()
    fireEvent.click(screen.getByRole('option', { name: /Task two/i }))
    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect.mock.calls[0][0].id).toBe('run-2')
    expect(onClose).toHaveBeenCalled()
  })

  it('shows the empty copy when nothing matches', () => {
    render(
      <SessionPicker
        open
        agentName="Codey"
        sessions={[]}
        onClose={() => undefined}
        onSelect={() => undefined}
      />,
    )
    expect(screen.getByText('no sessions yet')).toBeInTheDocument()
  })
})
