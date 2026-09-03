import { fireEvent, render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import TeamComposer from '../TeamComposer'
import { DRAG_MIME, encodeDragAgent } from '../../lib/teamRoster'
import type { TeamAgent } from '../../lib/api'

const AGENTS: TeamAgent[] = [
  { id: 'jeeves', name: 'Jeeves', kind: 'api', source: 'blueprint:jeeves' },
  { id: 'grok', name: 'grok', kind: 'cli', source: 'cli:grok' },
  {
    id: 'acp',
    name: 'ACP harness',
    kind: 'remote',
    source: 'placeholder:remote:acp',
    placeholder: true,
  },
]

function mockDataTransfer(initial: Record<string, string> = {}) {
  const store = { ...initial }
  return {
    store,
    setData: (type: string, value: string) => {
      store[type] = value
    },
    getData: (type: string) => store[type] ?? '',
    effectAllowed: 'copy' as const,
    dropEffect: 'copy' as const,
  }
}

function renderComposer() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <TeamComposer isOpen onClose={() => {}} />
    </QueryClientProvider>,
  )
}

describe('TeamComposer first-launch overlay', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/v1/team-agents')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ object: 'list', data: AGENTS }),
          } as Response
        }
        if (url.includes('/v1/team-rosters')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ object: 'list', data: [] }),
          } as Response
        }
        return { ok: false, status: 404, json: async () => ({}) } as Response
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders two panes: dashed drop zone and available agents', async () => {
    renderComposer()

    const dropZone = await screen.findByTestId('team-drop-zone')
    expect(dropZone).toHaveClass('border-dashed')
    expect(dropZone).toHaveTextContent(/drop agents here/i)

    const available = await screen.findByRole('list', { name: /available agents list/i })
    expect(within(available).getByText('Jeeves')).toBeInTheDocument()
    expect(within(available).getAllByText('API').length).toBeGreaterThan(0)
    expect(within(available).getAllByText('CLI').length).toBeGreaterThan(0)
    expect(within(available).getAllByText('remote').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: /new team/i })).toBeInTheDocument()
  })

  it('defaults handoff and as_tool on, and states gate is unwired', async () => {
    renderComposer()
    const handoff = await screen.findByRole('checkbox', { name: /handoff/i })
    const asTool = screen.getByRole('checkbox', { name: /as_tool/i })
    expect(handoff).toBeChecked()
    expect(asTool).toBeChecked()
    expect(screen.getByText(/gate is unwired/i)).toBeInTheDocument()
  })

  it('adds a member via native HTML5 drop', async () => {
    renderComposer()
    const dropZone = await screen.findByTestId('team-drop-zone')
    const payload = encodeDragAgent(AGENTS[0])
    const dt = mockDataTransfer({ [DRAG_MIME]: payload })
    fireEvent.drop(dropZone, { dataTransfer: dt })

    const roster = await screen.findByRole('list', { name: /roster members/i })
    expect(within(roster).getByText('jeeves')).toBeInTheDocument()
    expect(within(roster).getByText('API')).toBeInTheDocument()
    expect(within(roster).getByDisplayValue('default')).toBeInTheDocument()
  })

  it('adds and removes via context menu for a11y', async () => {
    renderComposer()
    const available = await screen.findByRole('list', { name: /available agents list/i })
    const grokRow = within(available).getByText('grok').closest('li')
    expect(grokRow).toBeTruthy()
    fireEvent.contextMenu(grokRow as HTMLElement)
    fireEvent.click(screen.getByRole('menuitem', { name: /^add$/i }))

    const roster = await screen.findByRole('list', { name: /roster members/i })
    expect(within(roster).getByText('CLI')).toBeInTheDocument()

    const chip = within(roster).getByText('grok').closest('article') as HTMLElement
    fireEvent.contextMenu(chip)
    fireEvent.click(screen.getByRole('menuitem', { name: /^remove$/i }))
    expect(screen.queryByRole('list', { name: /roster members/i })).not.toBeInTheDocument()
    expect(screen.getByText(/drop agents here/i)).toBeInTheDocument()
  })

  it('saves the roster contract without posting to /v1/teams/', async () => {
    const fetchMock = vi.mocked(fetch)
    renderComposer()
    const dropZone = await screen.findByTestId('team-drop-zone')
    fireEvent.drop(dropZone, {
      dataTransfer: mockDataTransfer({ [DRAG_MIME]: encodeDragAgent(AGENTS[1]) }),
    })
    fireEvent.change(screen.getByLabelText(/team name/i), {
      target: { value: 'Research Squad' },
    })

    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input)
      if (init?.method === 'POST') {
        expect(url).toContain('/v1/team-rosters/')
        expect(url).not.toContain('/v1/teams/')
        const body = JSON.parse(String(init?.body))
        expect(body.name).toBe('Research Squad')
        expect(body.members[0]).toMatchObject({
          id: 'grok',
          kind: 'cli',
          role: 'default',
          source: 'cli:grok',
        })
        expect(body.wires).toEqual({ handoff: true, as_tool: true })
        return {
          ok: true,
          status: 201,
          json: async () => ({
            id: 'research-squad',
            object: 'team_roster',
            name: 'Research Squad',
            members: body.members,
            wires: body.wires,
          }),
        } as Response
      }
      if (url.includes('/v1/team-agents')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ object: 'list', data: AGENTS }),
        } as Response
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: [] }),
      } as Response
    })

    fireEvent.click(screen.getByRole('button', { name: /save roster/i }))
    expect(await screen.findByRole('status')).toHaveTextContent(/team_rosters\.json/i)
  })

  it('marks available rows as HTML5-draggable (no dnd-kit)', async () => {
    renderComposer()
    const available = await screen.findByRole('list', { name: /available agents list/i })
    const row = within(available).getByText('Jeeves').closest('[draggable]')
    expect(row).toHaveAttribute('draggable', 'true')
  })
})
