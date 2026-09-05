import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AgentSidebar from '../AgentSidebar'

describe('REQ-216: Remote/team stack — normal avatar if 1 member; mini stack only for 2+', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    localStorage.clear()
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    global.fetch = vi.fn().mockImplementation(async (input: RequestInfo) => {
      const url = String(input)
      if (url.includes('/v1/preferences')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            object: 'user_preferences',
            principal: 'session:test',
            guest: true,
            empty: true,
            favourites: [],
            hidden_agents: [],
          }),
        } as Response
      }
      if (url.includes('team_rosters') || url.includes('team-rosters')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            object: 'list',
            data: [
              {
                id: 'solo-team',
                name: 'Solo Team',
                description: 'Team with 1 member',
                members: [{ id: 'solo-bot', name: 'Solo Bot', role: 'lead' }],
              },
              {
                id: 'duo-team',
                name: 'Duo Team',
                description: 'Team with 2 members',
                members: [
                  { id: 'bot-1', name: 'Bot 1', role: 'lead' },
                  { id: 'bot-2', name: 'Bot 2', role: 'worker' },
                ],
              },
            ],
          }),
        } as Response
      }
      if (url.includes('remotes')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            data: [
              {
                id: 'hermes',
                title: 'Hermes',
                configured: true,
                agents: [{ id: 'hermes-1', name: 'Hermes', started_at: '2026-09-03T00:00:00Z' }],
              },
              {
                id: 'duo-remote',
                title: 'Duo Remote',
                configured: true,
                agents: [
                  { id: 'r1', name: 'R1', started_at: '2026-09-03T00:00:00Z' },
                  { id: 'r2', name: 'R2', started_at: '2026-09-03T00:00:01Z' },
                ],
              },
            ],
          }),
        } as Response
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: [] }),
      } as Response
    })
  })

  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('renders single normal-size avatar (no mini stack) when team has only 1 member', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AgentSidebar open />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const solo = await within(list).findByRole('link', { name: /Solo Team \(team\)/ })

    // Solo team has 1 member -> single normal-size avatar, no AvatarStack
    expect(solo).toHaveAttribute('data-stack-count', '1')
    expect(within(solo).queryByLabelText('Solo Team members')).not.toBeInTheDocument()
    expect(solo.querySelector('[data-agent-avatar]')).toBeInTheDocument()
    expect(solo.querySelectorAll('.os-avatar-stack__face')).toHaveLength(0)
    expect(within(solo).queryByText(/^\+\d+$/)).not.toBeInTheDocument()
  })

  it('renders mini stacked avatars when team has 2 or more members', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AgentSidebar open />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const duo = await within(list).findByRole('link', { name: /Duo Team \(team\)/ })

    // Duo team has 2 members -> mini stacked avatars
    expect(duo).toHaveAttribute('data-stack-count', '2')
    const stack = within(duo).getByLabelText('Duo Team members')
    expect(stack).toHaveAttribute('data-avatar-stack', 'true')
    expect(duo.querySelectorAll('.os-avatar-stack__face')).toHaveLength(2)
  })

  it('renders single normal-size avatar (no mini stack) when remote has only 1 member', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AgentSidebar open />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const hermes = await within(list).findByRole('link', { name: /Hermes \(remote\)/ })

    // Hermes has 1 member -> single normal-size avatar
    expect(hermes).toHaveAttribute('data-stack-count', '1')
    expect(within(hermes).queryByLabelText('Hermes members')).not.toBeInTheDocument()
    expect(hermes.querySelector('[data-agent-avatar]')).toBeInTheDocument()
    expect(hermes.querySelectorAll('.os-avatar-stack__face')).toHaveLength(0)
  })

  it('renders mini stacked avatars when remote has 2 or more members', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AgentSidebar open />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const duoRemote = await within(list).findByRole('link', { name: /Duo Remote \(remote\)/ })

    // Duo remote has 2 members -> mini stacked avatars
    expect(duoRemote).toHaveAttribute('data-stack-count', '2')
    const stack = within(duoRemote).getByLabelText('Duo Remote members')
    expect(stack).toHaveAttribute('data-avatar-stack', 'true')
    expect(duoRemote.querySelectorAll('.os-avatar-stack__face')).toHaveLength(2)
  })
})
