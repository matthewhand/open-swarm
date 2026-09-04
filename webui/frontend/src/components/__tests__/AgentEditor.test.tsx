import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AgentEditor from '../AgentEditor'
import SettingsSheet, { OPEN_SETTINGS_EVENT, type OpenSettingsDetail } from '../SettingsSheet'
import { ToastProvider } from '../DaisyUI'
import { AGENT_EDITS_KEY, assignedBlueprintId } from '../../lib/agentEdits'

const catalog = [
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

function stubCatalog() {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/v1/models')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            object: 'list',
            data: [{ id: 'default', object: 'model', created: 0, owned_by: 'swarm' }],
          }),
        } as Response
      }
      if (url.includes('/v1/blueprints') && url.includes('/source')) {
        return {
          ok: false,
          status: 404,
          json: async () => ({ error: 'blueprint not found' }),
        } as Response
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: catalog }),
      } as Response
    }),
  )
}

function renderEditor({
  isOpen = true,
  agentId = 'support',
}: {
  isOpen?: boolean
  agentId?: string
} = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const onClose = vi.fn()
  const view = render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <AgentEditor isOpen={isOpen} onClose={onClose} agentId={agentId} />
      </ToastProvider>
    </QueryClientProvider>,
  )
  return { ...view, onClose, client }
}

function EditorThenSettings({ agentId = 'support' }: { agentId?: string }) {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsBlueprintId, setSettingsBlueprintId] = useState<string | null>(null)
  const [editorOpen, setEditorOpen] = useState(true)

  useEffect(() => {
    const onOpen = (event: Event) => {
      const detail = (event as CustomEvent<OpenSettingsDetail>).detail
      setSettingsBlueprintId(detail?.blueprintId ?? null)
      setSettingsOpen(true)
    }
    window.addEventListener(OPEN_SETTINGS_EVENT, onOpen)
    return () => window.removeEventListener(OPEN_SETTINGS_EVENT, onOpen)
  }, [])

  return (
    <ToastProvider>
      <AgentEditor isOpen={editorOpen} onClose={() => setEditorOpen(false)} agentId={agentId} />
      <SettingsSheet
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        blueprintId={settingsBlueprintId}
      />
    </ToastProvider>
  )
}

describe('AgentEditor (REQ-58)', () => {
  afterEach(() => {
    localStorage.removeItem(AGENT_EDITS_KEY)
    vi.unstubAllGlobals()
  })

  it('is agent-scoped: name, role, blueprint picker — no Remotes or System nav', async () => {
    stubCatalog()
    renderEditor()

    const dialog = await screen.findByRole('dialog', { name: /Edit /i, hidden: true })
    expect(dialog).toHaveClass('modal')
    expect(within(dialog).getByLabelText('Name')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Role')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Blueprint')).toBeInTheDocument()
    expect(within(dialog).queryByRole('button', { name: 'Remotes' })).not.toBeInTheDocument()
    expect(within(dialog).queryByRole('button', { name: 'System' })).not.toBeInTheDocument()
    expect(within(dialog).queryByRole('button', { name: /CLI catalog/i })).not.toBeInTheDocument()
    expect(within(dialog).queryByRole('navigation', { name: 'Settings sections' })).not.toBeInTheDocument()
    expect(within(dialog).queryByText('Hermes')).not.toBeInTheDocument()
    expect(await within(dialog).findByRole('button', { name: /Edit blueprint/i })).toBeInTheDocument()
  })

  it('assigns a blueprint from the picker and persists it on that agent', async () => {
    stubCatalog()
    renderEditor({ agentId: 'support' })

    const picker = await screen.findByLabelText('Blueprint')
    await waitFor(() => {
      expect(within(picker).getByRole('option', { name: 'Codey' })).toBeInTheDocument()
    })
    fireEvent.change(picker, { target: { value: 'codey' } })
    expect(assignedBlueprintId('support')).toBe('codey')
    expect(JSON.parse(localStorage.getItem(AGENT_EDITS_KEY) || '{}').support.blueprintId).toBe(
      'codey',
    )
    expect(picker).toHaveValue('codey')
  })

  it('Edit blueprint opens Settings → Blueprints with the assigned item selected', async () => {
    stubCatalog()
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    render(
      <QueryClientProvider client={client}>
        <EditorThenSettings agentId="support" />
      </QueryClientProvider>,
    )

    const picker = await screen.findByLabelText('Blueprint')
    await waitFor(() => {
      expect(within(picker).getByRole('option', { name: 'Codey' })).toBeInTheDocument()
    })
    fireEvent.change(picker, { target: { value: 'codey' } })
    fireEvent.click(screen.getByRole('button', { name: /Edit blueprint/i }))

    const settings = await screen.findByRole('dialog', { name: 'Settings', hidden: true })
    const nav = within(settings).getByRole('navigation', { name: 'Settings sections' })
    expect(within(nav).getByRole('button', { name: 'Blueprints' })).toHaveClass('menu-active')
    expect(within(nav).getByRole('button', { name: 'Remotes' })).toBeInTheDocument()

    const list = within(settings).getByRole('listbox', { name: 'Blueprints' })
    const selected = within(list).getByRole('option', { name: 'Codey' })
    expect(selected).toHaveAttribute('aria-selected', 'true')
    expect(selected).toHaveClass('menu-active')
    expect(within(list).getByRole('option', { name: 'Support' })).toHaveAttribute(
      'aria-selected',
      'false',
    )
  })
})
