import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AgentSidebar from '../AgentSidebar'

describe('REQ-217: Unpinned agent labels — shared left vertical alignment', () => {
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
                id: 'multi-team',
                name: 'Multi Team',
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
            object: 'list',
            data: [
              {
                id: 'remote-1',
                title: 'Remote Cluster',
                configured: true,
                endpoint: 'http://localhost:9000',
                agents: ['r1', 'r2'],
              },
            ],
          }),
        } as Response
      }
      if (url.includes('blueprints')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            object: 'list',
            data: [
              { id: 'codey', name: 'Codey', role: 'default', description: 'Writes code' },
              { id: 'tester', name: 'Tester', role: 'support', description: 'Tests code' },
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

  it('renders all unpinned rows with shared os-agent-row__avatar-slot and os-agent-row__label-col', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AgentSidebar open />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codeyRow = await within(list).findByRole('link', { name: /codey/i })
    const testerRow = await within(list).findByRole('link', { name: /tester/i })
    const soloTeamRow = await within(list).findByRole('link', { name: /solo team/i })
    const multiTeamRow = await within(list).findByRole('link', { name: /multi team/i })
    const remoteRow = await within(list).findByRole('link', { name: /remote cluster/i })

    const rows = [codeyRow, testerRow, soloTeamRow, multiTeamRow, remoteRow]

    for (const row of rows) {
      expect(row.className).toContain('os-agent-row')
      const avatarSlot = row.querySelector('.os-agent-row__avatar-slot')
      expect(avatarSlot).toBeInTheDocument()

      const labelCol = row.querySelector('.os-agent-row__label-col')
      expect(labelCol).toBeInTheDocument()

      // The label column starts immediately after the avatar slot in the DOM
      expect(avatarSlot?.nextElementSibling).toBe(labelCol)
    }
  })
})
