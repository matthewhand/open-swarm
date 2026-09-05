import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TeammateTaskCard } from '../TeammateTaskCard'
import type { RemoteConnection } from '../../lib/api'
import type { TeamRoster } from '../../lib/teamRosters'
import type { TeammateTaskEvent } from '../../lib/teammateTask'

const HERMES_UI = 'http://127.0.0.1:9119/stub-hermes'
const OMB_WORD = /\bOMB\b/

const harnessTeam: TeamRoster = {
  id: 'harness-team',
  name: 'Harness Team',
  description: '',
  members: [
    { id: 'hermes', name: 'Hermes', kind: 'remote', role: 'default' },
    { id: 'omb', name: 'OpenMousBot', kind: 'remote', role: 'default' },
  ],
}

const localTeam: TeamRoster = {
  id: 'local-team',
  name: 'Local Team',
  description: '',
  members: [{ id: 'codey', name: 'Codey', kind: 'api', role: 'default' }],
}

const hermesRemote: RemoteConnection = {
  id: 'hermes',
  kind: 'hermes',
  title: 'Hermes',
  base_url: 'http://127.0.0.1:8642',
  ui_url: HERMES_UI,
  source: 'config',
}

function event(extra: Partial<TeammateTaskEvent> = {}): TeammateTaskEvent {
  return {
    type: 'teammate_task',
    teamId: 'harness-team',
    workerId: 'hermes',
    workerKind: 'hermes',
    title: 'list sessions',
    status: 'Done',
    ...extra,
  }
}

describe('TeammateTaskCard', () => {
  it('team + stub Hermes: Open in Hermes uses the stub URL', () => {
    render(
      <TeammateTaskCard
        event={event()}
        context={{ teamId: 'harness-team', team: harnessTeam, remotes: [hermesRemote] }}
      />,
    )
    const card = screen.getByTestId('teammate-task-card')
    expect(card).toHaveClass('card')
    expect(screen.getByTestId('teammate-task-title')).toHaveTextContent('list sessions')
    expect(screen.getByText('Done')).toBeInTheDocument()
    const open = screen.getByTestId('teammate-task-open')
    expect(open).toHaveTextContent('Open in Hermes')
    expect(open).toHaveAttribute('href', HERMES_UI)
    expect(open).toHaveAttribute('target', '_blank')
    expect(card.textContent).not.toMatch(OMB_WORD)
    expect(card.textContent).not.toMatch(/Open in Cursor/i)
  })

  it('OpenMousBot label never contains OMB', () => {
    render(
      <TeammateTaskCard
        event={event({ workerId: 'omb', workerKind: 'omb', openInLabel: 'Open in OpenMousBot' })}
        context={{
          teamId: 'harness-team',
          team: harnessTeam,
          remotes: [
            {
              id: 'omb',
              kind: 'omb',
              title: 'OpenMousBot',
              base_url: 'http://127.0.0.1:8802',
              source: 'config',
            },
          ],
        }}
      />,
    )
    const open = screen.getByTestId('teammate-task-open')
    expect(open).toHaveTextContent('Open in OpenMousBot')
    expect(open.textContent).not.toMatch(OMB_WORD)
  })

  it('no remote on the team: no Open-in button', () => {
    render(
      <TeammateTaskCard
        event={event({ teamId: 'local-team', workerId: 'codey', workerKind: undefined })}
        context={{ teamId: 'local-team', team: localTeam, remotes: [hermesRemote] }}
      />,
    )
    expect(screen.queryByTestId('teammate-task-open')).not.toBeInTheDocument()
    expect(screen.getByTestId('teammate-task-card').textContent).not.toMatch(/Open in /)
  })

  it('empty remote config disables Open in Hermes with an honest reason', () => {
    render(
      <TeammateTaskCard
        event={event({ disabledReason: 'No UI URL configured for Hermes' })}
        context={{
          teamId: 'harness-team',
          team: harnessTeam,
          remotes: [{ ...hermesRemote, ui_url: '', base_url: '' }],
        }}
      />,
    )
    const open = screen.getByTestId('teammate-task-open')
    expect(open).toBeDisabled()
    expect(open).toHaveTextContent('Open in Hermes')
    expect(open).not.toHaveAttribute('href')
    expect(open).toHaveAttribute('aria-label', 'No UI URL configured for Hermes')
  })
})
