import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import StackedAvatars from '../StackedAvatars'
import { stackAvatarDelayMs, type AgentSession } from '../../lib/scaleOutSessions'

function session(id: string, startedAt: number, status: AgentSession['status'] = 'running'): AgentSession {
  return {
    id,
    agentId: 'codey',
    title: id,
    snippet: `${id} snippet`,
    status,
    startedAt,
    updatedAt: startedAt,
  }
}

describe('StackedAvatars', () => {
  it('animates four stacked faces with distinct delays from startedAt', () => {
    const sessions = [
      session('face-a', 1_000),
      session('face-b', 1_200),
      session('face-c', 1_400),
      session('face-d', 1_600),
    ]
    render(<StackedAvatars sessions={sessions} maxFaces={4} />)

    const faces = screen.getAllByTestId('os-stacked-avatar')
    expect(faces).toHaveLength(4)
    expect(screen.queryByTestId('os-stacked-remainder')).not.toBeInTheDocument()

    const started = faces.map((face) => Number(face.getAttribute('data-started-at')))
    const origin = Math.min(...started)
    const delays = faces.map((face) => face.style.animationDelay)
    expect(new Set(delays).size).toBe(4)
    faces.forEach((face, index) => {
      expect(face).toHaveClass('os-stacked-avatar--pulse')
      expect(face.style.animationDelay).toBe(
        `${stackAvatarDelayMs(started[index] ?? 0, origin)}ms`,
      )
    })
  })

  it('shows three faces plus remainder for four concurrent sessions', () => {
    render(
      <StackedAvatars
        sessions={[
          session('r1', 100),
          session('r2', 200),
          session('r3', 300),
          session('r4', 400),
        ]}
      />,
    )
    expect(screen.getAllByTestId('os-stacked-avatar')).toHaveLength(3)
    expect(screen.getByTestId('os-stacked-remainder')).toHaveTextContent('+1')
  })
})
