import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import AgentSidebar from '../AgentSidebar'
import { HIDDEN_AGENTS_STORAGE_KEY } from '../../lib/hiddenAgents'
import { PINNED_AGENTS_STORAGE_KEY } from '../../lib/pinnedAgents'
import { HOSTNAME_STORAGE_KEY } from '../../lib/hostname'

function blueprint(id: string, name: string, description: string, role?: string) {
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
    ...(role ? { role } : {}),
  }
}

const blueprints = [
  blueprint('codey', 'Codey', 'Code assistant'),
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

function renderSidebar(initialEntry = '/chat', onOpenSearch = () => undefined) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <AgentSidebar open onClose={() => undefined} onOpenSearch={onOpenSearch} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function storedHidden(): string[] {
  return JSON.parse(localStorage.getItem(HIDDEN_AGENTS_STORAGE_KEY) || '[]')
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

  it('seeds Hidden with gate and skeptic on first load; Support stays visible', async () => {
    renderSidebar()

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const support = await within(list).findByRole('link', { name: /Support/ })
    expect(within(list).getAllByRole('link')[0]).toBe(support)
    expect(support.className).toMatch(/os-agent-row--support/)
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

  it('reveals a focusable hover-edit on role rows and opens Settings via Enter', async () => {
    // REQ-26 first-load seed hides gate/skeptic; show all roles for this check.
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify([]))
    const opened: Array<{ blueprintId?: string }> = []
    const onOpen = (event: Event) => {
      opened.push((event as CustomEvent).detail || {})
    }
    window.addEventListener('swarm:open-settings', onOpen)
    renderSidebar()

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const supportEdit = await screen.findByRole('button', { name: 'Edit Support blueprint' })
    expect(screen.getByRole('button', { name: 'Edit Gate blueprint' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit Skeptic blueprint' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit Codey blueprint' })).not.toBeInTheDocument()
    expect(within(list).queryByRole('menuitem', { name: /Hide all/i })).not.toBeInTheDocument()

    supportEdit.focus()
    fireEvent.keyDown(supportEdit, { key: 'Enter' })
    expect(opened).toEqual([{ section: 'blueprint', blueprintId: 'support' }])
    window.removeEventListener('swarm:open-settings', onOpen)
  })

  it('shows a distinct CoS badge and nested team rows with a Team badge', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const cos = await within(list).findByRole('link', { name: /Pat/ })
    expect(cos).toHaveAttribute('data-role', 'chief_of_staff')
    expect(cos).toHaveClass('os-agent-role-chief_of_staff')
    expect(cos).toHaveClass('os-agent-row--cos')
    expect(within(cos).getByText('CoS')).toHaveAttribute('data-role', 'chief_of_staff')

    const office = within(list).getByRole('link', { name: /Office/ })
    expect(office).toHaveAttribute('data-kind', 'team')
    expect(within(office).getByText('Team')).toHaveAttribute('data-kind', 'team')

    const research = within(list).getByRole('link', { name: /Research/ })
    expect(research).toHaveAttribute('data-kind', 'team')
    expect(research.closest('ul')).toHaveClass('os-agent-team-nest')
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

  it('selects a team like an agent via ?team=', async () => {
    renderSidebar('/chat?team=demo-team')

    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const team = await within(list).findByRole('link', { name: /Demo Team \(team\)/ })
    expect(team).toHaveAttribute('aria-current', 'page')
    expect(within(list).getByRole('link', { name: /Codey/ })).not.toHaveAttribute(
      'aria-current',
    )
  })
})

const SCALE_MEMBERS = [
  { id: 'cos', name: 'Pat', kind: 'agent', role: 'chief_of_staff', started_at: '2026-09-03T00:00:00Z', status: 'running' },
  { id: 'ada', name: 'Ada', kind: 'agent', started_at: '2026-09-03T00:00:01Z', status: 'finished' },
  { id: 'bea', name: 'Bea', kind: 'agent', started_at: '2026-09-03T00:00:02Z', status: 'running' },
  { id: 'cyd', name: 'Cyd', kind: 'agent', started_at: '2026-09-03T00:00:03Z', status: 'running' },
  { id: 'dee', name: 'Dee', kind: 'agent', started_at: '2026-09-03T00:00:04Z', status: 'running' },
]

const STACK_REMOTES = {
  object: 'list',
  data: [
    {
      id: 'omb',
      title: 'OMB',
      configured: true,
      agents: [
        { id: 'omb-cos', name: 'CoS', started_at: '2026-09-03T00:00:00Z', role: 'chief_of_staff' },
        { id: 'w1', name: 'Worker 1', started_at: '2026-09-03T00:00:01Z' },
        { id: 'w2', name: 'Worker 2', started_at: '2026-09-03T00:00:02Z' },
        { id: 'w3', name: 'Worker 3', started_at: '2026-09-03T00:00:03Z' },
        { id: 'w4', name: 'Worker 4', started_at: '2026-09-03T00:00:04Z' },
      ],
    },
    {
      id: 'hermes',
      title: 'Hermes',
      configured: true,
      agents: [{ id: 'hermes-1', name: 'Hermes', started_at: '2026-09-03T00:00:00Z' }],
    },
    {
      id: 'rakazo',
      title: 'Rakazo',
      configured: true,
      agents: [
        { id: 'r1', name: 'Rakazo A', started_at: '2026-09-03T00:00:00Z' },
        { id: 'r2', name: 'Rakazo B', started_at: '2026-09-03T00:00:01Z' },
      ],
    },
    {
      id: 'lab-swarm',
      kind: 'open-swarm',
      title: 'Lab swarm',
      configured: true,
      agents: [
        { id: 'ns-cos', name: 'CoS', started_at: '2026-09-03T00:00:00Z' },
        { id: 'ns-w', name: 'Nested worker', started_at: '2026-09-03T00:00:01Z' },
      ],
    },
  ],
}

describe('AgentSidebar stacked avatars (REQ-68)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/v1/remotes')) {
          return {
            ok: true,
            status: 200,
            json: async () => STACK_REMOTES,
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
                  id: 'scale-out',
                  object: 'team_roster',
                  name: 'Scale Out',
                  description: 'Five workers',
                  members: SCALE_MEMBERS,
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

  it('stacks 3 most recent team faces + remainder on one rail row', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const team = await within(list).findByRole('link', { name: /Scale Out \(team\)/ })
    expect(team).toHaveAttribute('data-stack-count', '3')
    expect(team).toHaveAttribute('data-remainder', '2')
    const stack = within(team).getByLabelText('Scale Out members')
    expect(stack).toHaveAttribute('data-avatar-stack', 'true')
    expect(stack).toHaveAttribute('data-stack-count', '3')
    expect(within(stack).getByText('+2')).toBeInTheDocument()
    const faces = team.querySelectorAll('.os-avatar-stack__face')
    expect(faces).toHaveLength(3)
    expect(
      [...faces].every((face) => face.classList.contains('os-avatar-stack__face--working')),
    ).toBe(true)
    const delays = [...faces].map((face) => (face as HTMLElement).style.animationDelay)
    expect(new Set(delays).size).toBe(3)
    expect(delays).toContain('0ms')
  })

  it('keeps a single-agent remote as one avatar (no stack)', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const hermes = await within(list).findByRole('link', { name: /Hermes \(remote\)/ })
    expect(hermes).toHaveAttribute('data-stack-count', '1')
    expect(hermes).toHaveAttribute('data-remainder', '0')
    const stack = within(hermes).getByLabelText('Hermes members')
    expect(stack).toHaveAttribute('data-avatar-stack', 'false')
    expect(within(hermes).queryByText(/^\+\d+$/)).not.toBeInTheDocument()
    expect(hermes.querySelectorAll('.os-avatar-stack__face')).toHaveLength(1)
  })

  it('labels OpenMousBot (not OMB) and stacks CoS + workers; click opens filtered picker', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const omb = await within(list).findByRole('link', { name: /OpenMousBot \(remote\)/ })
    expect(omb).toHaveTextContent('OpenMousBot')
    expect(omb).not.toHaveTextContent(/\bOMB\b/)
    expect(omb).toHaveAttribute('data-stack-count', '3')
    expect(omb).toHaveAttribute('data-remainder', '2')
    expect(within(list).getByRole('link', { name: /Rakazo \(remote\)/ })).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: /Lab swarm \(remote\)/ })).toBeInTheDocument()

    fireEvent.click(omb)
    const dialog = await screen.findByRole('dialog', { name: 'OpenMousBot sessions' })
    expect(within(dialog).getAllByRole('option')).toHaveLength(5)
    expect(dialog).toHaveTextContent('OpenMousBot')
    expect(dialog).not.toHaveTextContent(/\bOMB\b/)
    fireEvent.change(within(dialog).getByRole('combobox', { name: 'Filter sessions' }), {
      target: { value: 'Worker 1' },
    })
    expect(within(dialog).getAllByRole('option')).toHaveLength(1)
    fireEvent.click(within(dialog).getByRole('option', { name: /Worker 1/ }))
    expect(screen.queryByRole('dialog', { name: 'OpenMousBot sessions' })).not.toBeInTheDocument()
  })

  it('opens the team picker filtered to that roster and selects a session id', async () => {
    renderSidebar('/chat?team=scale-out')
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const team = await within(list).findByRole('link', { name: /Scale Out \(team\)/ })
    fireEvent.click(team)
    const dialog = await screen.findByRole('dialog', { name: 'Scale Out sessions' })
    expect(within(dialog).getAllByRole('option')).toHaveLength(5)
    expect(within(dialog).getByRole('option', { name: /Pat/ })).toHaveAttribute(
      'data-session-id',
      'scale-out:cos',
    )
    fireEvent.change(within(dialog).getByRole('combobox', { name: 'Filter sessions' }), {
      target: { value: 'cyd' },
    })
    expect(within(dialog).getAllByRole('option')).toHaveLength(1)
    fireEvent.click(within(dialog).getByRole('option', { name: /Cyd/ }))
    expect(screen.queryByRole('dialog', { name: 'Scale Out sessions' })).not.toBeInTheDocument()
  })
})
