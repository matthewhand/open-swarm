import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SessionPicker from '../SessionPicker'
import type { MemberSession } from '../../lib/sessionPicker'

const sessions: MemberSession[] = [
  {
    id: 'scale:cos',
    groupId: 'scale',
    groupKind: 'team',
    memberId: 'cos',
    title: 'Pat',
    snippet: 'chief_of_staff',
    status: 'running',
    startedAt: 1000,
    href: '/chat?team=scale&session=cos',
  },
  {
    id: 'scale:ada',
    groupId: 'scale',
    groupKind: 'team',
    memberId: 'ada',
    title: 'Ada',
    snippet: 'done',
    status: 'finished',
    startedAt: 2000,
    href: '/chat?team=scale&session=ada',
  },
]

describe('SessionPicker', () => {
  it('filters the pre-scoped list and click selects that session id', () => {
    const onSelect = vi.fn()
    render(
      <SessionPicker
        open
        title="Scale"
        sessions={sessions}
        onClose={() => undefined}
        onSelect={onSelect}
      />,
    )
    expect(screen.getByRole('dialog', { name: 'Scale sessions' })).toBeInTheDocument()
    expect(screen.getAllByRole('option')).toHaveLength(2)
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter sessions' }), {
      target: { value: 'ada' },
    })
    expect(screen.getAllByRole('option')).toHaveLength(1)
    fireEvent.click(screen.getByRole('option', { name: /Ada/ }))
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 'scale:ada' }))
  })

  it('shows no sessions yet when the group is empty', () => {
    render(
      <SessionPicker
        open
        title="Quiet"
        sessions={[]}
        onClose={() => undefined}
        onSelect={() => undefined}
      />,
    )
    expect(screen.getByText('no sessions yet')).toBeInTheDocument()
  })
})
