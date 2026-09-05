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

  it('keeps New session available when the list is empty', () => {
    const onNew = vi.fn()
    const onClose = vi.fn()
    render(
      <SessionPicker
        open
        agentName="Codey"
        sessions={[]}
        onClose={onClose}
        onSelect={() => undefined}
        onNewSession={onNew}
      />,
    )
    expect(screen.getByText('no sessions yet')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /^New session$/i }))
    expect(onNew).toHaveBeenCalledTimes(1)
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

  it('renders a Manage Team footer link when sessions are for a team', () => {
    const onClose = vi.fn()
    render(
      <SessionPicker
        open
        title="Core Team"
        sessions={[
          {
            id: 'core-team:alice',
            groupId: 'core-team',
            groupKind: 'team',
            memberId: 'alice',
            title: 'Alice',
            snippet: 'coder',
            status: 'running',
            startedAt: 1000,
            href: '/chat?team=core-team&session=alice',
          },
        ]}
        onClose={onClose}
        onSelect={() => undefined}
      />,
    )
    const link = screen.getByRole('link', { name: /Manage Team/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/teams/#core-team')
    fireEvent.click(link)
    expect(onClose).toHaveBeenCalled()
  })
})
