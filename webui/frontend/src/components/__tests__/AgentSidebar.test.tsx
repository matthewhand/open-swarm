import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, useSearchParams } from 'react-router-dom'
import AgentSidebar from '../AgentSidebar'
import { HIDDEN_AGENTS_STORAGE_KEY } from '../../lib/hiddenAgents'
import { PINNED_AGENTS_STORAGE_KEY } from '../../lib/pinnedAgents'
import { HOSTNAME_STORAGE_KEY } from '../../lib/hostname'
import {
  GENERATION_COMPLETE_EVENT,
  RAIL_ORDER_STORAGE_KEY,
} from '../../lib/railOrder'
import { BUMP_COMPLETED_KEY } from '../../lib/settingsPrefs'
import { saveAgentSessions, type AgentSession } from '../../lib/scaleOutSessions'

function blueprint(
  id: string,
  name: string,
  description: string,
  role?: string,
  avatar_path?: string,
) {
  const actualRole = role && !role.startsWith('/') ? role : undefined
  const actualAvatar = avatar_path || (role && role.startsWith('/') ? role : undefined)
  return {
    id,
    object: 'blueprint' as const,
    name,
    description,
    abbreviation: null,
    required_mcp_servers: [] as string[],
    tags: [] as string[],
    installed: true,
    compiled: true,
    ...(actualRole ? { role: actualRole } : {}),
    ...(actualAvatar ? { avatar_path: actualAvatar } : {}),
  }
}

const blueprints = [
  blueprint('codey', 'Codey', 'Code assistant', '/avatars/codey_avatar.png'),
  blueprint('stewie', 'Stewie', 'Helpful agent'),
  blueprint('gate', 'Gate', 'Role: gate'),
  blueprint('skeptic', 'Skeptic', 'Role: skeptic'),
  blueprint('cos', 'Pat', 'Talks to any team.', 'chief_of_staff'),
]

const rosters = [
  {
    id: 'office',
    object: 'team_roster' as const,
    name: 'Office',
    members: [
      { id: 'research', kind: 'team', team_id: 'research', role: 'default', source: 'team:research' },
    ],
    wires: { handoff: true, as_tool: true },
  },
  {
    id: 'research',
    object: 'team_roster' as const,
    name: 'Research',
    members: [{ id: 'ada', kind: 'api', role: 'default', source: 'blueprint:ada' }],
    wires: { handoff: true, as_tool: true },
  },
]

function mockDataTransfer() {
  const store = new Map<string, string>()
  return {
    setData: (type: string, value: string) => {
      store.set(type, value)
    },
    getData: (type: string) => store.get(type) || '',
    effectAllowed: 'copyMove' as const,
    dropEffect: 'move' as const,
    types: [] as string[],
  }
}

function dragTo(source: Element, target: Element) {
  const dataTransfer = mockDataTransfer()
  fireEvent.dragStart(source, { dataTransfer })
  fireEvent.dragEnter(target, { dataTransfer })
  fireEvent.dragOver(target, { dataTransfer })
  fireEvent.drop(target, { dataTransfer })
  fireEvent.dragEnd(source, { dataTransfer })
}

function mockFetch(extraBlueprints = blueprints, extraRosters = rosters) {
  return vi.fn().mockImplementation(async (input: RequestInfo) => {
    const url = String(input)
    if (url.includes('team_rosters') || url.includes('team-rosters')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: extraRosters }),
      } as Response
    }
    if (url.includes('/v1/cli-agents')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          clis: ['grok', 'agy', 'opencode', 'pi'],
          native_consensus: {},
          catalog: {},
          rail: [
            { id: 'grok_agent', object: 'cli.agent', name: 'grok_agent', cli: 'grok', kind: 'cli', description: 'Host grok CLI', installed: true },
            { id: 'agy_agent', object: 'cli.agent', name: 'agy_agent', cli: 'agy', kind: 'cli', description: 'Host agy CLI', installed: true },
            { id: 'opencode_agent', object: 'cli.agent', name: 'opencode_agent', cli: 'opencode', kind: 'cli', description: 'Host opencode CLI', installed: true },
            { id: 'pi_agent', object: 'cli.agent', name: 'pi_agent', cli: 'pi', kind: 'cli', description: 'Host pi CLI', installed: true },
          ],
        }),
      } as Response
    }
    if (url.includes('/v1/herdr-agents')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          object: 'list',
          data: [
            {
              id: 1,
              object: 'herdr.agent',
              kind: 'herdr',
              name: 'w3:p1',
              remote: '',
              created_at: '2026-09-03T00:00:00Z',
              updated_at: '2026-09-03T00:00:00Z',
            },
          ],
        }),
      } as Response
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({ object: 'list', data: extraBlueprints }),
    } as Response
  })
}

function SearchProbe() {
  const [params] = useSearchParams()
  return <span data-testid="os-test-search">{params.toString()}</span>
}

function renderSidebar(initialEntry = '/chat', onOpenSearch = () => undefined) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <AgentSidebar open onClose={() => undefined} onOpenSearch={onOpenSearch} />
        <SearchProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function storedHidden(): string[] {
  return JSON.parse(localStorage.getItem(HIDDEN_AGENTS_STORAGE_KEY) || '[]')
}

function storedRailOrder(): string[] {
  return JSON.parse(localStorage.getItem(RAIL_ORDER_STORAGE_KEY) || '[]')
}

function railIds(list: HTMLElement): string[] {
  return [...list.querySelectorAll('[data-rail-id]')].map(
    (node) => node.getAttribute('data-rail-id') || '',
  )
}

describe('AgentSidebar Grok rail', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', mockFetch())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('lists Support first and does not filter the catalog from the rail Search field', async () => {
    const onOpenSearch = vi.fn()
    renderSidebar('/chat', onOpenSearch)

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const support = await within(list).findByRole('link', { name: /Support/ })
    const links = within(list).getAllByRole('link')
    expect(links[0]).toBe(support)
    expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: /Stewie/ })).toBeInTheDocument()
    expect(within(list).queryByRole('link', { name: /Gate/ })).not.toBeInTheDocument()
    expect(within(list).queryByRole('link', { name: /Skeptic/ })).not.toBeInTheDocument()

    const search = screen.getByRole('searchbox', { name: 'Search' })
    expect(search).toHaveAttribute('placeholder', 'Search')
    fireEvent.focus(search)
    fireEvent.click(search)
    expect(onOpenSearch).toHaveBeenCalled()
    expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: /Stewie/ })).toBeInTheDocument()
  })

  it('paints the same custom face on the Codey rail tile as the header would', async () => {
    renderSidebar('/chat?blueprint=codey')
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    const face = codey.querySelector('[data-agent-avatar]')
    expect(face).toHaveAttribute('data-agent-avatar', 'custom')
    expect(codey.querySelector('img')).toHaveAttribute('src', '/avatars/codey_avatar.png')
    const support = within(list).getByRole('link', { name: /Support/ })
    expect(support.querySelector('[data-agent-avatar]')).toHaveAttribute(
      'data-agent-avatar',
      'default',
    )
  })

  it('lists grok_agent, agy_agent, opencode_agent, and pi_agent after Support', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    await within(list).findByRole('link', { name: /grok_agent/ })
    const hrefs = within(list)
      .getAllByRole('link')
      .map((el) => el.getAttribute('href'))
    expect(hrefs.slice(0, 5)).toEqual([
      '/chat?blueprint=support',
      '/chat?blueprint=grok_agent',
      '/chat?blueprint=agy_agent',
      '/chat?blueprint=opencode_agent',
      '/chat?blueprint=pi_agent',
    ])
  })

  it('keeps CLI rail rows listed even if they were previously hidden', async () => {
    localStorage.setItem(
      HIDDEN_AGENTS_STORAGE_KEY,
      JSON.stringify(['grok_agent', 'agy_agent', 'opencode_agent', 'pi_agent', 'codey']),
    )
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    await within(list).findByRole('link', { name: /grok_agent/ })
    expect(within(list).getByRole('link', { name: /agy_agent/ })).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: /opencode_agent/ })).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: /pi_agent/ })).toBeInTheDocument()
    expect(within(list).queryByRole('link', { name: /Codey/ })).not.toBeInTheDocument()
  })
  })

  it('seeds Hidden with gate and skeptic on first load; Support stays visible', async () => {
    renderSidebar()

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const support = await within(list).findByRole('link', { name: /Support/ })
    expect(within(list).getAllByRole('link')[0]).toBe(support)
    expect(support.className).not.toMatch(/os-agent-row--support/)
    expect(support.className).not.toMatch(/os-agent-role-/)
    expect(support.querySelector('.os-agent-role-badge')).toHaveTextContent('Support')
    expect(within(list).queryByRole('link', { name: /Gate/ })).not.toBeInTheDocument()
    expect(within(list).queryByRole('link', { name: /Skeptic/ })).not.toBeInTheDocument()

    await waitFor(() => {
      expect(storedHidden()).toEqual(['gate', 'skeptic'])
    })
    fireEvent.click(screen.getByRole('button', { name: /2 hidden/i }))
    const dialog = await screen.findByRole('dialog', { name: /Hidden agents/i })
    expect(within(dialog).getByText('Gate')).toBeInTheDocument()
    expect(within(dialog).getByText('Skeptic')).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: /Unhide Gate/i }))
    await waitFor(() => {
      expect(storedHidden()).toEqual(['skeptic'])
    })
    expect(within(list).getByRole('link', { name: /Gate/ })).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: /Support/ })).toBeInTheDocument()
  })

  it('does not re-seed when the user already customized hidden agents', async () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(['codey']))
    renderSidebar()

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    await waitFor(() => {
      expect(within(list).queryByRole('link', { name: /Codey/ })).not.toBeInTheDocument()
    })
    expect(within(list).getByRole('link', { name: /Support/ })).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: /Gate/ })).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: /Skeptic/ })).toBeInTheDocument()
    expect(storedHidden()).toEqual(['codey'])
  })

  it('hides from the list via context menu and unhides from the end-of-list popup', async () => {
    renderSidebar()

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })

    fireEvent.contextMenu(codey)
    fireEvent.click(await screen.findByRole('menuitem', { name: /Hide from sidebar/i }))

    await waitFor(() => {
      expect(within(list).queryByRole('link', { name: /Codey/ })).not.toBeInTheDocument()
    })
    expect(within(list).getByRole('link', { name: /Stewie/ })).toBeInTheDocument()
    expect(storedHidden()).toEqual(['gate', 'skeptic', 'codey'])
    expect(screen.queryByRole('menuitem', { name: /Hide all/i })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /3 hidden/i }))
    const dialog = await screen.findByRole('dialog', { name: /Hidden agents/i })
    fireEvent.click(within(dialog).getByRole('button', { name: /Unhide Codey/i }))
    await waitFor(() => {
      expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()
    })
    expect(storedHidden()).toEqual(['gate', 'skeptic'])
    expect(screen.getByRole('button', { name: /2 hidden/i })).toBeInTheDocument()
  })

  it('opens the agent-scoped editor from the context menu', async () => {
    const opened: Array<{ agentId?: string }> = []
    const onOpen = (event: Event) => {
      opened.push((event as CustomEvent).detail || {})
    }
    window.addEventListener('swarm:open-agent-editor', onOpen)
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    fireEvent.contextMenu(codey)
    fireEvent.click(await screen.findByRole('menuitem', { name: /^Edit agent$/i }))
    expect(opened).toEqual([{ agentId: 'codey', agentName: 'Codey' }])
    window.removeEventListener('swarm:open-agent-editor', onOpen)
  })

  it('pins from the context menu onto the unlabeled favourite grid', async () => {
    renderSidebar()

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    fireEvent.contextMenu(codey)
    fireEvent.click(await screen.findByRole('menuitem', { name: /^Pin$/i }))

    const grid = screen.getByLabelText('Pinned agents')
    expect(within(grid).getByRole('link', { name: 'Codey' })).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()
    expect(JSON.parse(localStorage.getItem(PINNED_AGENTS_STORAGE_KEY) || '[]')).toEqual([
      { id: 'codey', name: 'Codey' },
    ])
  })

  it('exposes Plugins and an editable hostname after the conversation list', async () => {
    renderSidebar()
    await screen.findByRole('navigation', { name: 'Agent list' })
    expect(screen.getByRole('button', { name: /Plugins/i })).toBeInTheDocument()
    const hostname = screen.getByLabelText('Hostname')
    fireEvent.change(hostname, { target: { value: 'lab-box' } })
    fireEvent.blur(hostname)
    expect(localStorage.getItem(HOSTNAME_STORAGE_KEY)).toBe('lab-box')
  })

  it('always shows a Hidden drop zone, including when empty', async () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify([]))
    renderSidebar()
    await screen.findByRole('navigation', { name: 'Agent list' })
    const zone = screen.getByRole('region', { name: 'Hidden' })
    expect(zone).toHaveClass('os-drop-target')
    expect(zone).toHaveTextContent(/drop here to hide/i)
    expect(screen.queryByRole('button', { name: /Hide all/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^\d+ hidden$/i })).not.toBeInTheDocument()
  })

  it('drags a support agent onto Hidden and persists the id', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const support = await within(list).findByRole('link', { name: /Support/ })
    const zone = screen.getByRole('region', { name: 'Hidden' })

    fireEvent.dragStart(support, { dataTransfer: mockDataTransfer() })
    expect(support).toHaveClass('os-agent-row--dragging')
    fireEvent.dragOver(zone, { dataTransfer: mockDataTransfer() })
    expect(zone).toHaveAttribute('data-drag-over', 'true')
    expect(zone).toHaveClass('os-drop-target')

    dragTo(support, zone)

    await waitFor(() => {
      expect(within(list).queryByRole('link', { name: /Support/ })).not.toBeInTheDocument()
    })
    expect(storedHidden()).toEqual(['gate', 'skeptic', 'support'])
    expect(screen.getByRole('button', { name: /3 hidden/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Hide all/i })).not.toBeInTheDocument()
  })

  it('drags a default agent onto Hidden; Unhide restores; no Hide-all', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    const zone = screen.getByRole('region', { name: 'Hidden' })

    dragTo(codey, zone)

    await waitFor(() => {
      expect(within(list).queryByRole('link', { name: /Codey/ })).not.toBeInTheDocument()
    })
    expect(storedHidden()).toEqual(['gate', 'skeptic', 'codey'])
    expect(screen.queryByRole('button', { name: /Hide all/i })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /3 hidden/i }))
    const dialog = await screen.findByRole('dialog', { name: /Hidden agents/i })
    fireEvent.click(within(dialog).getByRole('button', { name: /Unhide Codey/i }))
    await waitFor(() => {
      expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()
    })
    expect(storedHidden()).toEqual(['gate', 'skeptic'])
    expect(screen.getByRole('button', { name: /2 hidden/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Hide all/i })).not.toBeInTheDocument()
  })

  it('hides role agents (gate, skeptic) via the Hidden drop zone', async () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify([]))
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const zone = screen.getByRole('region', { name: 'Hidden' })

    dragTo(await within(list).findByRole('link', { name: /Gate/ }), zone)
    dragTo(await within(list).findByRole('link', { name: /Skeptic/ }), zone)

    await waitFor(() => {
      expect(within(list).queryByRole('link', { name: /Gate/ })).not.toBeInTheDocument()
      expect(within(list).queryByRole('link', { name: /Skeptic/ })).not.toBeInTheDocument()
    })
    expect(storedHidden()).toEqual(['gate', 'skeptic'])
  })

  it('no-ops when a row is dropped onto itself', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    dragTo(codey, codey)
    expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()
    expect(storedHidden()).toEqual(['gate', 'skeptic'])
  })

  it('removes a pinned favourite from the pin grid when hidden', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    fireEvent.contextMenu(codey)
    fireEvent.click(await screen.findByRole('menuitem', { name: /^Pin$/i }))
    const grid = screen.getByLabelText('Pinned agents')
    expect(within(grid).getByRole('link', { name: 'Codey' })).toBeInTheDocument()

    dragTo(codey, screen.getByRole('region', { name: 'Hidden' }))

    await waitFor(() => {
      expect(within(list).queryByRole('link', { name: /Codey/ })).not.toBeInTheDocument()
    })
    expect(within(grid).queryByRole('link', { name: 'Codey' })).not.toBeInTheDocument()
    expect(JSON.parse(localStorage.getItem(PINNED_AGENTS_STORAGE_KEY) || '[]')).toEqual([])
    expect(storedHidden()).toEqual(['gate', 'skeptic', 'codey'])
  })

  it('lists persisted Herdr members (kind=herdr) so Teams/sidepane can pick them', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const herdr = await within(list).findByRole('link', { name: /w3:p1/ })
    expect(herdr).toHaveAttribute('href', '/teams/#herdr-members')
    expect(herdr).toHaveTextContent(/Herdr · localhost/)
  })

  it('opens the definition Settings pane when a role badge is clicked', async () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify([]))
    const opened: Array<Record<string, unknown>> = []
    const onOpen = (event: Event) => {
      opened.push((event as CustomEvent).detail || {})
    }
    window.addEventListener('swarm:open-settings', onOpen)
    renderSidebar()

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const badge = await within(list).findByRole('button', { name: 'Open gate settings' })
    expect(badge).toHaveAttribute('data-definition-id', 'gate')
    fireEvent.click(badge)
    expect(opened).toEqual([
      {
        section: 'definition',
        definitionKind: 'role',
        definitionId: 'gate',
        blueprintId: 'gate',
      },
    ])
    window.removeEventListener('swarm:open-settings', onOpen)
  })

  it('reveals a focusable hover-edit on role rows and opens the agent editor via Enter', async () => {
    // REQ-26 first-load seed hides gate/skeptic; show all roles for this check.
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify([]))
    const opened: Array<{ agentId?: string }> = []
    const onOpen = (event: Event) => {
      opened.push((event as CustomEvent).detail || {})
    }
    window.addEventListener('swarm:open-agent-editor', onOpen)
    renderSidebar()

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const supportEdit = await screen.findByRole('button', { name: 'Edit Support' })
    expect(screen.getByRole('button', { name: 'Edit Gate' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit Skeptic' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit Codey' })).not.toBeInTheDocument()
    expect(within(list).queryByRole('menuitem', { name: /Hide all/i })).not.toBeInTheDocument()

    supportEdit.focus()
    fireEvent.keyDown(supportEdit, { key: 'Enter' })
    expect(opened).toEqual([{ agentId: 'support' }])
    window.removeEventListener('swarm:open-agent-editor', onOpen)
  })

  it('persists a native drag reorder and leaves favourite tiles alone', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const stewie = await within(list).findByRole('link', { name: /Stewie/ })
    const support = await within(list).findByRole('link', { name: /Support/ })
    const codey = within(list).getByRole('link', { name: /Codey/ })

    fireEvent.contextMenu(codey)
    fireEvent.click(await screen.findByRole('menuitem', { name: /^Pin$/i }))
    const grid = screen.getByLabelText('Pinned agents')
    expect(within(grid).getByRole('link', { name: 'Codey' })).toBeInTheDocument()

    expect(railIds(list)[0]).toBe('support')
    dragTo(stewie, support)

    await waitFor(() => {
      expect(railIds(list)[0]).toBe('stewie')
    })
    expect(storedRailOrder()[0]).toBe('stewie')
    expect(within(list).getByRole('link', { name: /Support/ })).toBeInTheDocument()
    expect(within(grid).getByRole('link', { name: 'Codey' })).toBeInTheDocument()
    expect(JSON.parse(localStorage.getItem(PINNED_AGENTS_STORAGE_KEY) || '[]')).toEqual([
      { id: 'codey', name: 'Codey' },
    ])
    expect(within(grid).getAllByRole('link').map((link) => link.getAttribute('aria-label'))).toEqual([
      'Codey',
    ])
  })

  it('reloads a persisted rail order without scrambling favourite tiles', async () => {
    localStorage.setItem(RAIL_ORDER_STORAGE_KEY, JSON.stringify(['stewie', 'support', 'codey']))
    localStorage.setItem(
      PINNED_AGENTS_STORAGE_KEY,
      JSON.stringify([{ id: 'codey', name: 'Codey' }]),
    )
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    await waitFor(() => {
      expect(railIds(list)[0]).toBe('stewie')
    })
    const grid = screen.getByLabelText('Pinned agents')
    expect(within(grid).getByRole('link', { name: 'Codey' })).toBeInTheDocument()
    expect(within(grid).getAllByRole('link')).toHaveLength(1)
  })

  it('moves a just-completed fixture to index 0 when bump is on', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    await within(list).findByRole('link', { name: /Stewie/ })
    expect(railIds(list)[0]).toBe('support')

    fireEvent(window, new CustomEvent(GENERATION_COMPLETE_EVENT, { detail: { agentId: 'stewie' } }))

    await waitFor(() => {
      expect(railIds(list)[0]).toBe('stewie')
    })
    expect(storedRailOrder()[0]).toBe('stewie')
  })

  it('does not bump a completed fixture when the toggle is off', async () => {
    localStorage.setItem(BUMP_COMPLETED_KEY, '0')
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    await within(list).findByRole('link', { name: /Stewie/ })
    expect(railIds(list)[0]).toBe('support')

    fireEvent(window, new CustomEvent(GENERATION_COMPLETE_EVENT, { detail: { agentId: 'stewie' } }))

    expect(railIds(list)[0]).toBe('support')
    expect(storedRailOrder()).toEqual([])
  })

  it('keeps a scale-out agent as one stacked row and opens a session picker', async () => {
    const running: AgentSession[] = [1, 2, 3, 4].map((n) => ({
      id: `run-${n}`,
      agentId: 'codey',
      title: `Task ${n}`,
      snippet: `work ${n}`,
      status: 'running',
      startedAt: n * 200,
      updatedAt: n * 200,
    }))
    saveAgentSessions('codey', [
      ...running,
      {
        id: 'fin-1',
        agentId: 'codey',
        title: 'Old job',
        snippet: 'finished fixture',
        status: 'finished',
        startedAt: 50,
        updatedAt: 50,
      },
    ])
    renderSidebar('/chat?blueprint=codey')

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('button', { name: /Codey, 5 sessions/i })
    const rows = list.querySelectorAll('[data-agent-id="codey"]')
    expect(rows).toHaveLength(1)
    expect(within(list).queryByRole('link', { name: /Codey/ })).not.toBeInTheDocument()
    expect(codey).toHaveAttribute('data-scale-out', 'true')

    const faces = within(codey).getAllByTestId('os-stacked-avatar')
    expect(faces).toHaveLength(3)
    expect(within(codey).getByTestId('os-stacked-remainder')).toHaveTextContent('+1')
    const delays = faces.map((face) => face.style.animationDelay)
    expect(new Set(delays).size).toBe(3)
    for (const face of faces) {
      expect(face).toHaveClass('os-stacked-avatar--pulse')
    }

    fireEvent.click(codey)
    const dialog = await screen.findByRole('dialog', { name: 'Codey sessions' })
    const options = within(dialog).getAllByRole('option')
    expect(options).toHaveLength(5)
    expect(within(dialog).getByText('finished fixture', { exact: false })).toBeInTheDocument()

    fireEvent.change(screen.getByRole('combobox', { name: /Filter Codey sessions/i }), {
      target: { value: 'Task 2' },
    })
    expect(within(dialog).getAllByRole('option')).toHaveLength(1)
    fireEvent.click(within(dialog).getByRole('option', { name: /Task 2/i }))
    expect(screen.queryByRole('dialog', { name: 'Codey sessions' })).not.toBeInTheDocument()
    expect(screen.getByTestId('os-test-search').textContent).toContain('session=run-2')
    expect(screen.getByTestId('os-test-search').textContent).toContain('blueprint=codey')
  })

  it('shows a distinct CoS badge and nested team rows with a Team badge', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const cos = await within(list).findByRole('link', { name: /Pat/ })
    expect(cos).not.toHaveClass('os-agent-role-chief_of_staff')
    expect(cos).not.toHaveClass('os-agent-row--cos')
    expect(cos.className).not.toMatch(/os-agent-role-/)
    const cosBadge = within(cos).getByText('CoS')
    expect(cosBadge).toHaveAttribute('data-role', 'chief_of_staff')
    expect(cosBadge).toHaveClass('os-agent-role-badge')
    expect(cosBadge).toHaveClass('os-agent-role-chief_of_staff')

    const office = within(list).getByRole('link', { name: /Office/ })
    expect(office).toHaveAttribute('data-kind', 'team')
    expect(within(office).getByText('Team')).toHaveAttribute('data-kind', 'team')

    const research = within(list).getByRole('link', { name: /Research/ })
    expect(research).toHaveAttribute('data-kind', 'team')
    expect(research.closest('ul')).toHaveClass('os-agent-team-nest')
  })

  it('REQ-67: role chrome is the badge only — no row fill/border', async () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify([]))
    renderSidebar('/chat?blueprint=codey')

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const support = await within(list).findByRole('link', { name: /Support/ })
    const gate = within(list).getByRole('link', { name: /Gate/ })
    const skeptic = within(list).getByRole('link', { name: /Skeptic/ })
    const cos = within(list).getByRole('link', { name: /Pat/ })
    const codey = within(list).getByRole('link', { name: /Codey/ })

    for (const row of [support, gate, skeptic, cos, codey]) {
      expect(row).toHaveClass('os-agent-row')
      expect(row.className).not.toMatch(/os-agent-row--(support|gate|skeptic|cos|chief_of_staff)/)
      expect(row.className).not.toMatch(/os-agent-role-/)
      expect(row.querySelector('.os-agent-dot')).not.toHaveAttribute('data-role')
    }

    expect(support.querySelector('.os-agent-role-badge')).toHaveAttribute('data-role', 'support')
    expect(gate.querySelector('.os-agent-role-badge')).toHaveAttribute('data-role', 'gate')
    expect(skeptic.querySelector('.os-agent-role-badge')).toHaveAttribute('data-role', 'skeptic')
    expect(cos.querySelector('.os-agent-role-badge')).toHaveAttribute('data-role', 'chief_of_staff')
    expect(codey.querySelector('.os-agent-role-badge')).toBeNull()

    expect(codey).toHaveClass('os-agent-row--active')
    expect(support).not.toHaveClass('os-agent-row--active')
    expect(support.closest('.os-agent-row-wrap')?.className).not.toMatch(/os-agent-role-/)
  })

  it('nested team row keeps ?team= and does not clobber with ?blueprint= (REQ-28 / #345)', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const research = await within(list).findByRole('link', { name: /Research \(team\)/ })
    expect(research).toHaveAttribute('href', '/chat?team=research')
    expect(research.getAttribute('href')).not.toMatch(/blueprint=/)
    const office = within(list).getByRole('link', { name: /Office \(team\)/ })
    expect(office).toHaveAttribute('href', '/chat?team=office')
  })

  it('Plugins overlay is an empty honest dialog over the rail (PR #322)', async () => {
    renderSidebar()
    await screen.findByRole('navigation', { name: 'Agent list' })
    fireEvent.click(screen.getByRole('button', { name: /Plugins/i }))
    const dialog = screen.getByRole('dialog', { name: 'Plugins' })
    expect(dialog).toHaveTextContent(/No plugins installed/i)
    expect(within(dialog).queryByRole('link')).not.toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Close plugins' }))
    expect(screen.queryByRole('dialog', { name: 'Plugins' })).not.toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Agent list' })).toBeInTheDocument()
  })
})

describe('AgentSidebar special roles', () => {
  const roster = [
    {
      id: 'codey',
      object: 'blueprint' as const,
      name: 'Codey',
      description: 'Code',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
      role: null,
    },
    {
      id: 'skeptic',
      object: 'blueprint' as const,
      name: 'Skeptic',
      description: 'Retry stub',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
      role: 'skeptic',
    },
    {
      id: 'gate',
      object: 'blueprint' as const,
      name: 'Gate',
      description: 'Approve stub',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
      role: 'gate',
    },
    {
      id: 'support',
      object: 'blueprint' as const,
      name: 'Support',
      description: 'Onboarding. First team.',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
      role: 'support',
    },
  ]

  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: roster }),
      } as Response),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('lists Support first with a role=support look, not a diamond', async () => {
    renderSidebar('/chat?blueprint=support')
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    await waitFor(() => {
      expect(within(list).getAllByRole('link').length).toBeGreaterThan(0)
    })
    const links = within(list).getAllByRole('link')
    expect(links[0]).toHaveTextContent('Support')
    expect(links[0].querySelector('[data-role="support"]')).not.toBeNull()
  })
})

describe('AgentSidebar teams', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('team_rosters') || url.includes('team-rosters')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              object: 'list',
              data: [
                {
                  id: 'demo-team',
                  object: 'team_roster',
                  name: 'Demo Team',
                  description: 'Example multi-agent roster',
                  members: [
                    { id: 'codey', name: 'Codey', kind: 'agent', role: 'coder' },
                  ],
                },
              ],
            }),
          } as Response
        }
        if (url.includes('/v1/herdr-agents')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ object: 'list', data: [] }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ object: 'list', data: blueprints }),
        } as Response
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('mixes a visually distinct team row with agent rows', async () => {
    renderSidebar()

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const team = await within(list).findByRole('link', { name: /Demo Team \(team\)/ })
    expect(team).toHaveAttribute('href', '/chat?team=demo-team')
    expect(team.className).toMatch(/os-team-item/)
    expect(within(team).getByText('Team')).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: /Stewie/ })).toBeInTheDocument()
  })

  it('opens the definition pane when the Team badge is clicked', async () => {
    const opened: Array<Record<string, unknown>> = []
    const onOpen = (event: Event) => {
      opened.push((event as CustomEvent).detail || {})
    }
    window.addEventListener('swarm:open-settings', onOpen)
    renderSidebar()

    const badge = await screen.findByRole('button', { name: 'Open Demo Team team settings' })
    fireEvent.click(badge)
    expect(opened).toEqual([
      {
        section: 'definition',
        definitionKind: 'team',
        definitionId: 'demo-team',
        teamId: 'demo-team',
      },
    ])
    window.removeEventListener('swarm:open-settings', onOpen)
  })

  it('selects a team like an agent via ?team=', async () => {
    renderSidebar('/chat?team=demo-team')

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const team = await within(list).findByRole('link', { name: /Demo Team \(team\)/ })
    expect(team).toHaveAttribute('aria-current', 'page')
    expect(within(list).getByRole('link', { name: /Codey/ })).not.toHaveAttribute(
      'aria-current',
    )
  })

  it('REQ-24 #342: hides a team roster row as team:<id> and Unhide restores it', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const team = await within(list).findByRole('link', { name: /Demo Team \(team\)/ })
    const zone = screen.getByRole('region', { name: 'Hidden' })
    dragTo(team, zone)

    await waitFor(() => {
      expect(within(list).queryByRole('link', { name: /Demo Team \(team\)/ })).not.toBeInTheDocument()
    })
    expect(storedHidden()).toEqual(['gate', 'skeptic', 'team:demo-team'])

    fireEvent.click(screen.getByRole('button', { name: /3 hidden/i }))
    const dialog = await screen.findByRole('dialog', { name: /Hidden agents/i })
    expect(within(dialog).getByText('Demo Team')).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: /Unhide Demo Team/i }))
    await waitFor(() => {
      expect(within(list).getByRole('link', { name: /Demo Team \(team\)/ })).toBeInTheDocument()
    })
    expect(storedHidden()).toEqual(['gate', 'skeptic'])
  })
})

describe('AgentSidebar pin unpin + plugins (REQ-5c #322)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', mockFetch())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('unpins from the context menu and clears swarm_pinned_agents', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    fireEvent.contextMenu(codey)
    fireEvent.click(await screen.findByRole('menuitem', { name: /^Pin$/i }))
    const grid = screen.getByLabelText('Pinned agents')
    expect(within(grid).getByRole('link', { name: 'Codey' })).toBeInTheDocument()

    fireEvent.contextMenu(codey)
    fireEvent.click(await screen.findByRole('menuitem', { name: /^Unpin$/i }))
    await waitFor(() => {
      expect(within(grid).queryByRole('link', { name: 'Codey' })).not.toBeInTheDocument()
    })
    expect(JSON.parse(localStorage.getItem(PINNED_AGENTS_STORAGE_KEY) || '[]')).toEqual([])
  })

  it('opens the Plugins dialog with the shipped empty copy and closes it', async () => {
    renderSidebar()
    await screen.findByRole('navigation', { name: 'Agent list' })
    fireEvent.click(screen.getByRole('button', { name: /Plugins/i }))
    const dialog = await screen.findByRole('dialog', { name: 'Plugins' })
    expect(within(dialog).getByText('No plugins installed.')).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Close plugins' }))
    expect(screen.queryByRole('dialog', { name: 'Plugins' })).not.toBeInTheDocument()
  })
})
