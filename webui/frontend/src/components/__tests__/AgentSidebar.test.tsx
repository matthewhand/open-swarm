import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import AgentSidebar from '../AgentSidebar'
import { AGENT_NAMES_STORAGE_KEY } from '../../lib/agentNames'
import { HIDDEN_AGENTS_STORAGE_KEY } from '../../lib/hiddenAgents'
import { PINNED_AGENTS_STORAGE_KEY } from '../../lib/pinnedAgents'
import { HOSTNAME_STORAGE_KEY } from '../../lib/hostname'

const blueprints = [
  {
    id: 'codey',
    object: 'blueprint' as const,
    name: 'Codey',
    description: 'Code assistant',
    abbreviation: null,
    required_mcp_servers: [],
    tags: [],
    installed: true,
    compiled: true,
  },
  {
    id: 'stewie',
    object: 'blueprint' as const,
    name: 'Stewie',
    description: 'Helpful agent',
    abbreviation: null,
    required_mcp_servers: [],
    tags: [],
    installed: true,
    compiled: true,
  },
]

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
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: blueprints }),
      } as Response),
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

    const search = screen.getByRole('searchbox', { name: 'Search' })
    expect(search).toHaveAttribute('placeholder', 'Search')
    fireEvent.focus(search)
    fireEvent.click(search)
    expect(onOpenSearch).toHaveBeenCalled()
    expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: /Stewie/ })).toBeInTheDocument()
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
    expect(storedHidden()).toEqual(['codey'])
    expect(screen.queryByRole('menuitem', { name: /Hide all/i })).not.toBeInTheDocument()

    const hiddenRow = within(list).getByRole('button', { name: /^Hidden Bots/ })
    expect(hiddenRow).toHaveTextContent('1')
    const listButtons = within(list).getAllByRole('button')
    expect(listButtons[listButtons.length - 1]).toBe(hiddenRow)
    fireEvent.click(hiddenRow)
    const dialog = await screen.findByRole('dialog', { name: /Hidden Bots/i })
    expect(dialog).toHaveTextContent(
      "Hidden Bots stay active and keep their history, they just don't show in the sidebar.",
    )
    fireEvent.click(within(dialog).getByRole('button', { name: /Unhide Codey/i }))
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /^Hidden Bots/ })).not.toBeInTheDocument()
    })
    expect(within(list).getByRole('link', { name: /Codey/ })).toBeInTheDocument()
    expect(storedHidden()).toEqual([])
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

  it('shows the last message as the subtitle, never agent.description', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo) => {
        const url = String(input)
        if (url.includes('/chat/thread/') && url.includes('codey')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              agent_id: 'codey',
              conversation_id: 'agt-codey',
              messages: [
                { role: 'user', content: 'prior question' },
                { role: 'assistant', content: 'ship the last line' },
              ],
            }),
          } as Response
        }
        if (url.includes('/chat/thread/')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ agent_id: 'x', conversation_id: 'x', messages: [] }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({ object: 'list', data: blueprints }),
        } as Response
      }),
    )

    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    expect(within(codey).getByText('ship the last line')).toBeInTheDocument()
    expect(within(codey).queryByText('Code assistant')).not.toBeInTheDocument()
    expect(screen.queryByText('Talk about the other agents.')).not.toBeInTheDocument()
    expect(screen.queryByText('Helpful agent')).not.toBeInTheDocument()
  })

  it('right-stacks role badges and uses role outline classes, not a purpose fill', async () => {
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const support = await within(list).findByRole('link', { name: /Support/ })
    const stack = within(support).getByTestId('agent-role-stack')
    expect(stack).toHaveClass('os-agent-role-stack')
    expect(stack).toHaveTextContent('support')
    expect(support.className).toContain('os-agent-row--support')
    expect(support.parentElement).toHaveAttribute('data-role', 'support')
    expect(within(list).queryByText('Talk about the other agents.')).not.toBeInTheDocument()
  })

  it('caps the Hidden dialog to the viewport and scrolls a long list', async () => {
    const crowd = Array.from({ length: 45 }, (_, index) => ({
      id: `bot-${index}`,
      object: 'blueprint' as const,
      name: `Bot ${index}`,
      description: 'purpose must not show',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
    }))
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(crowd.map((agent) => agent.id)))
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: crowd }),
      } as Response),
    )
    renderSidebar()
    const hiddenRow = await screen.findByRole('button', { name: /^Hidden Bots/ })
    expect(hiddenRow).toHaveTextContent('45')
    fireEvent.click(hiddenRow)
    const dialog = await screen.findByRole('dialog', { name: /Hidden Bots/i })
    expect(dialog).toHaveTextContent(
      "Hidden Bots stay active and keep their history, they just don't show in the sidebar.",
    )
    expect(dialog.className).toMatch(/max-h-\[calc\(100dvh-2rem\)\]/)
    const list = dialog.querySelector('ul')
    expect(list?.className).toMatch(/overflow-y-auto/)
    expect(list?.className).toMatch(/min-h-0/)
    expect(within(dialog).getAllByRole('button', { name: /Unhide/i })).toHaveLength(45)
    fireEvent.click(screen.getAllByRole('button', { name: 'Close hidden bots' })[0])
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /Hidden Bots/i })).not.toBeInTheDocument()
    })
  })

  it('shows a selected hidden agent in the main list with hidden border chrome', async () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(['codey']))
    const first = renderSidebar('/chat?blueprint=codey')
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    const codey = await within(list).findByRole('link', { name: /Codey/ })
    expect(codey).toHaveAttribute('data-hidden', 'selected')
    expect(codey.className).toContain('os-agent-row--hidden')
    expect(screen.getByRole('button', { name: /^Hidden Bots/ })).toHaveTextContent('1')
    first.unmount()

    renderSidebar('/chat?blueprint=stewie')
    const nextList = await screen.findByRole('navigation', { name: 'Agent list' })
    expect(await within(nextList).findByRole('link', { name: /Stewie/ })).toBeInTheDocument()
    expect(within(nextList).queryByRole('link', { name: /Codey/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /^Hidden Bots/ }))
    const dialog = await screen.findByRole('dialog', { name: /Hidden Bots/i })
    expect(within(dialog).getByText('Codey')).toBeInTheDocument()
  })

  it('uses a persisted name override on the rail', async () => {
    localStorage.setItem(AGENT_NAMES_STORAGE_KEY, JSON.stringify({ codey: 'Coder' }))
    renderSidebar()
    const list = await screen.findByRole('navigation', { name: 'Agent list' })
    expect(await within(list).findByRole('link', { name: /Coder/ })).toBeInTheDocument()
    expect(within(list).queryByRole('link', { name: /^Codey$/ })).not.toBeInTheDocument()
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
})
