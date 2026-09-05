import { createEvent, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AgentSidebar from '../AgentSidebar'
import { HIDDEN_AGENTS_STORAGE_KEY } from '../../lib/hiddenAgents'
import { PINNED_AGENTS_STORAGE_KEY } from '../../lib/pinnedAgents'
import { DELETED_RAIL_IDS_KEY } from '../../lib/deletedRailIds'

const blueprints = [
  {
    id: 'codey',
    object: 'blueprint' as const,
    name: 'Codey',
    description: 'Code assistant',
    abbreviation: null,
    required_mcp_servers: [] as string[],
    tags: [] as string[],
    installed: true,
    compiled: true,
  },
  {
    id: 'stewie',
    object: 'blueprint' as const,
    name: 'Stewie',
    description: 'Helpful agent',
    abbreviation: null,
    required_mcp_servers: [] as string[],
    tags: [] as string[],
    installed: true,
    compiled: true,
  },
]

function mockFetch() {
  return vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
    const url = String(input)
    const method = (init?.method || 'GET').toUpperCase()
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
      if (method === 'POST') {
        return {
          ok: true,
          status: 201,
          json: async () => ({
            object: 'team_roster',
            id: 'research-copy',
            name: 'Research copy',
            members: [],
            wires: { handoff: true, as_tool: true },
          }),
        } as Response
      }
      if (method === 'DELETE') {
        return { ok: true, status: 204, json: async () => ({}) } as Response
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({
          object: 'list',
          data: [
            {
              id: 'research',
              object: 'team_roster',
              name: 'Research',
              members: [{ id: 'ada', kind: 'api', role: 'default', source: 'blueprint:ada' }],
              wires: { handoff: true, as_tool: true },
            },
          ],
        }),
      } as Response
    }
    if (url.includes('/v1/cli-agents')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          clis: ['grok'],
          native_consensus: {},
          catalog: {},
          rail: [
            {
              id: 'cli_agent',
              object: 'cli.agent',
              name: 'cli_agent',
              cli: 'grok',
              kind: 'cli',
              description: 'Host CLI',
              installed: true,
            },
            {
              id: 'api_agent',
              object: 'cli.agent',
              name: 'api_agent',
              cli: '',
              kind: 'api',
              description: 'LiteLLM',
              installed: true,
            },
          ],
        }),
      } as Response
    }
    if (url.includes('/v1/remotes')) {
      if (method === 'POST') {
        return {
          ok: true,
          status: 201,
          json: async () => ({
            id: 'omb-copy',
            kind: 'omb',
            title: 'OpenMousBot copy',
            base_url: 'http://localhost:9',
            source: 'user',
          }),
        } as Response
      }
      if (method === 'DELETE') {
        return { ok: true, status: 204, json: async () => ({}) } as Response
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({
          object: 'list',
          data: [
            {
              id: 'omb',
              kind: 'omb',
              title: 'OpenMousBot',
              source: 'user',
              configured: true,
              base_url: 'http://localhost:9',
              agents: [{ id: 'cos', name: 'Pat' }],
            },
          ],
        }),
      } as Response
    }
    if (url.includes('/v1/herdr-agents')) {
      return { ok: true, status: 200, json: async () => ({ object: 'list', data: [] }) } as Response
    }
    if (url.includes('/v1/blueprints/custom') && method === 'POST') {
      return {
        ok: true,
        status: 201,
        json: async () => ({
          id: 'codey-copy',
          name: 'Codey copy',
          description: 'Copy of Codey',
          category: 'ai_assistants',
          tags: ['api'],
          code: '# copy',
        }),
      } as Response
    }
    if (url.includes('/v1/blueprints/custom') && method === 'DELETE') {
      return { ok: true, status: 204, json: async () => ({}) } as Response
    }
    return { ok: true, status: 200, json: async () => ({ object: 'list', data: blueprints }) } as Response
  })
}

function renderSidebar() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/chat']}>
        <AgentSidebar open onClose={() => undefined} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('REQ-82 rail right-click menu', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem(PINNED_AGENTS_STORAGE_KEY, '[]')
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify([]))
    vi.stubGlobal('fetch', mockFetch())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('opens a DaisyUI menu on right-click and prevents the browser default', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    const evt = createEvent.contextMenu(codey)
    fireEvent(codey, evt)
    expect(evt.defaultPrevented).toBe(true)
    const menu = await screen.findByRole('menu', { name: 'Actions for Codey' })
    expect(menu).toHaveClass('menu')
    expect(document.querySelector('.os-agent-edit')).not.toBeInTheDocument()
  })

  it('opens the same menu from Shift+F10 on a focused row', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    codey.focus()
    fireEvent.keyDown(codey, { key: 'F10', shiftKey: true })
    expect(await screen.findByRole('menu', { name: 'Actions for Codey' })).toBeInTheDocument()
  })

  it('requires confirm for Delete and keeps Delete last / danger', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    fireEvent.contextMenu(codey)
    const menu = await screen.findByRole('menu', { name: 'Actions for Codey' })
    const items = within(menu).getAllByRole('menuitem')
    expect(items.at(-1)).toHaveTextContent('Delete')
    expect(items.at(-1)).toHaveClass('text-error')
    fireEvent.click(items.at(-1)!)
    const dialog = await screen.findByRole('dialog', { name: /Delete Codey/i })
    expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()

    fireEvent.contextMenu(codey)
    fireEvent.click(await screen.findByRole('menuitem', { name: /^Delete$/i }))
    fireEvent.click(within(await screen.findByRole('dialog', { name: /Delete Codey/i })).getByRole('button', { name: 'Delete' }))
    await waitFor(() => {
      expect(within(list).queryByRole('link', { name: /Codey/ })).not.toBeInTheDocument()
    })
    expect(JSON.parse(localStorage.getItem(DELETED_RAIL_IDS_KEY) || '[]')).toContain('codey')
  })

  it('opens the agent editor for API Edit Profile and the remotes sheet for remotes', async () => {
    const opened: Array<Record<string, unknown>> = []
    const onOpen = (event: Event) => {
      opened.push((event as CustomEvent).detail || {})
    }
    window.addEventListener('swarm:open-agent-editor', onOpen)
    window.addEventListener('swarm:open-settings', onOpen)
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })

    fireEvent.contextMenu(await within(list).findByRole('link', { name: /Codey/ }))
    fireEvent.click(await screen.findByRole('menuitem', { name: /^Edit Profile$/i }))
    expect(opened).toContainEqual({ agentId: 'codey', agentName: 'Codey' })

    opened.length = 0
    fireEvent.contextMenu(await within(list).findByRole('link', { name: /Research \(team\)/ }))
    fireEvent.click(await screen.findByRole('menuitem', { name: /^Edit Profile$/i }))
    expect(opened).toContainEqual({
      section: 'definition',
      definitionKind: 'team',
      definitionId: 'research',
      teamId: 'research',
    })

    opened.length = 0
    fireEvent.contextMenu(await within(list).findByRole('link', { name: /OpenMousBot \(remote\)/ }))
    fireEvent.click(await screen.findByRole('menuitem', { name: /^Edit Profile$/i }))
    expect(opened).toContainEqual({ section: 'remotes' })

    fireEvent.contextMenu(await within(list).findByRole('link', { name: /cli_agent/ }))
    expect(screen.queryByRole('menuitem', { name: /^Edit Profile$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: /^Duplicate$/i })).not.toBeInTheDocument()
    window.removeEventListener('swarm:open-agent-editor', onOpen)
    window.removeEventListener('swarm:open-settings', onOpen)
  })

  it('copies the stored conversation id via the mocked clipboard', async () => {
    localStorage.setItem('swarm_agent_chat:codey', 'conv-codey-99')
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    fireEvent.contextMenu(await within(list).findByRole('link', { name: /Codey/ }))
    fireEvent.click(await screen.findByRole('menuitem', { name: /Copy conversation ID/i }))
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith('conv-codey-99')
    })
  })

  it('still hides from the sidebar via the menu', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    fireEvent.contextMenu(await within(list).findByRole('link', { name: /Stewie/ }))
    fireEvent.click(await screen.findByRole('menuitem', { name: /Hide from sidebar/i }))
    await waitFor(() => {
      expect(within(list).queryByRole('link', { name: /Stewie/ })).not.toBeInTheDocument()
    })
  })
})
