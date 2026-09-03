import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import AgentSidebar from '../AgentSidebar'
import { HIDDEN_AGENTS_STORAGE_KEY } from '../../lib/hiddenAgents'
import { PINNED_AGENTS_STORAGE_KEY } from '../../lib/pinnedAgents'
import { HOSTNAME_STORAGE_KEY } from '../../lib/hostname'
import {
  GENERATION_COMPLETE_EVENT,
  RAIL_ORDER_STORAGE_KEY,
} from '../../lib/railOrder'
import { BUMP_COMPLETED_KEY } from '../../lib/settingsPrefs'

function blueprint(id: string, name: string, description: string) {
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
  }
}

const blueprints = [
  blueprint('codey', 'Codey', 'Code assistant'),
  blueprint('stewie', 'Stewie', 'Helpful agent'),
  blueprint('gate', 'Gate', 'Role: gate'),
  blueprint('skeptic', 'Skeptic', 'Role: skeptic'),
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
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        const data = url.includes('/v1/herdr-agents')
          ? [{
              id: 1,
              object: 'herdr.agent' as const,
              kind: 'herdr' as const,
              name: 'w3:p1',
              remote: '',
              created_at: '2026-09-03T00:00:00Z',
              updated_at: '2026-09-03T00:00:00Z',
            }]
          : blueprints
        return {
          ok: true,
          status: 200,
          json: async () => ({ object: 'list', data }),
        } as Response
      }),
    )
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
