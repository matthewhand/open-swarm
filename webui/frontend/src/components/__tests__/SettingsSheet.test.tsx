import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import SettingsSheet from '../SettingsSheet'
import { ToastProvider } from '../DaisyUI'
import {
  BUMP_COMPLETED_KEY,
  HOSTNAME_OVERRIDE_KEY,
  RETENTION_MODE_KEY,
} from '../../lib/settingsPrefs'

function renderSheet({
  isOpen = true,
  blueprintId,
  initialSection,
  definitionKind,
  definitionId,
}: {
  isOpen?: boolean
  blueprintId?: string
  initialSection?: 'definition' | 'blueprint'
  definitionKind?: 'role' | 'blueprint' | 'team'
  definitionId?: string
} = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const onClose = vi.fn()
  const view = render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <SettingsSheet
          isOpen={isOpen}
          onClose={onClose}
          blueprintId={blueprintId}
          initialSection={initialSection}
          definitionKind={definitionKind}
          definitionId={definitionId}
        />
      </ToastProvider>
    </QueryClientProvider>,
  )
  return { ...view, onClose, client }
}

describe('SettingsSheet', () => {
  afterEach(() => {
    localStorage.removeItem(HOSTNAME_OVERRIDE_KEY)
    localStorage.removeItem(RETENTION_MODE_KEY)
    localStorage.removeItem(BUMP_COMPLETED_KEY)
    vi.unstubAllGlobals()
  })

  it('opens as a DaisyUI modal-end dialog with menu sections', () => {
    renderSheet()
    const dialog = screen.getByRole('dialog', { hidden: true })
    expect(dialog).toHaveClass('modal')
    expect(dialog).toHaveClass('modal-end')
    expect(dialog).not.toHaveClass('drawer')
    expect(dialog.className).not.toMatch(/btn-group/)

    const remotesToggle = screen.getByRole('button', { name: 'Remotes' })
    expect(remotesToggle).not.toHaveClass('menu-dropdown-toggle')
    expect(screen.getByRole('radiogroup', { name: 'Retention mode' })).toHaveClass('join')
    expect(screen.getByRole('button', { name: 'Definition' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Blueprint' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Hermes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'OMB' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Rakazo' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retention' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Hostname' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'LLM profiles' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Rail' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'System' })).toBeInTheDocument()
  })

  it('defaults the rail bump toggle on and persists off', () => {
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'Rail' }))
    const toggle = screen.getByRole('checkbox', { name: 'Bump completed agents to top' })
    expect(toggle).toBeChecked()
    fireEvent.click(toggle)
    expect(toggle).not.toBeChecked()
    expect(localStorage.getItem(BUMP_COMPLETED_KEY)).toBe('0')
  })

  it('shows remotes empty state and join radios for retention', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          object: 'list',
          kinds: [
            { id: 'hermes', label: 'Hermes' },
            { id: 'omb', label: 'OpenMousBot' },
            { id: 'rakazo', label: 'Rakazo' },
            { id: 'swarm', label: 'Swarm' },
          ],
          configured: [],
          data: [],
        }),
      } as Response),
    )
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'Remotes' }))
    expect(await screen.findByRole('button', { name: /Add remote/i })).toBeInTheDocument()
    expect(screen.getByText(/No remotes configured/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Hermes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'OMB' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Rakazo' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Swarm' })).not.toBeInTheDocument()
    expect(screen.queryByText(/\bOMB\b/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Add remote/i }))
    fireEvent.change(screen.getByRole('combobox', { name: 'Kind' }), {
      target: { value: 'swarm' },
    })
    expect(screen.getByText(/do not add this instance as its own remote/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Retention' }))
    const group = screen.getByRole('radiogroup', { name: 'Retention mode' })
    expect(group).toHaveClass('join')
    expect(screen.getByRole('radio', { name: 'Count' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Disk' })).toHaveClass('join-item')
    expect(screen.getByRole('radio', { name: 'Archive' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Trash' })).toBeInTheDocument()
  })

  it('LLM profiles shows the empty-models copy when /v1/models/ returns none', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: [] }),
      } as Response),
    )
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'LLM profiles' }))
    expect(await screen.findByText(/No models reported/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '/profiles/' })).toHaveAttribute('href', '/profiles/')
  })

  it('LLM profiles shows the operator fallback when /v1/models/ errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ error: 'down' }),
      } as Response),
    )
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'LLM profiles' }))
    expect(
      await screen.findByText(/Could not load models/i, undefined, { timeout: 4000 }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'LLM profiles' })).toHaveAttribute('href', '/profiles/')
  })

  it('adds an OpenMousBot remote then lists it in Settings and the dropdown', async () => {
    const configured: Array<Record<string, unknown>> = []
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input)
        const method = (init?.method || 'GET').toUpperCase()
        if (url.includes('/v1/remotes/') && method === 'POST') {
          const body = JSON.parse(String(init?.body || '{}')) as { kind?: string }
          const created = {
            id: body.kind || 'omb',
            kind: body.kind || 'omb',
            label: body.kind === 'omb' ? 'OpenMousBot' : body.kind,
            title: 'OpenMousBot',
            host_label: '',
            base_url: 'http://127.0.0.1:8802',
            source: 'config',
          }
          configured.push(created)
          return { ok: true, status: 201, json: async () => created } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({
            object: 'list',
            kinds: [
              { id: 'hermes', label: 'Hermes' },
              { id: 'omb', label: 'OpenMousBot' },
              { id: 'rakazo', label: 'Rakazo' },
            ],
            configured,
            data: [],
          }),
        } as Response
      }),
    )
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'Remotes' }))
    fireEvent.click(await screen.findByRole('button', { name: /Add remote/i }))
    const kindSelect = await screen.findByRole('combobox', { name: 'Kind' })
    expect(within(kindSelect).getByRole('option', { name: 'OpenMousBot' })).toBeInTheDocument()
    fireEvent.change(kindSelect, { target: { value: 'omb' } })
    expect(kindSelect).toHaveValue('omb')
    fireEvent.change(screen.getByRole('textbox', { name: 'URL' }), {
      target: { value: 'http://127.0.0.1:8802' },
    })
    fireEvent.submit(kindSelect.closest('form') as HTMLFormElement)

    const rows = await screen.findByRole('list', { name: 'Configured remotes' })
    expect(within(rows).getByText('OpenMousBot')).toBeInTheDocument()
    expect(within(rows).getByText('http://127.0.0.1:8802')).toBeInTheDocument()
    const remoteSelect = screen.getByRole('combobox', { name: 'Remote' })
    expect(within(remoteSelect).getByRole('option', { name: 'OpenMousBot' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'OMB' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'OMB' })).not.toBeInTheDocument()
  })
  })

  it('persists retention via join radios and shows a save toast', async () => {
    renderSheet()
    fireEvent.click(screen.getByRole('radio', { name: 'Archive' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save retention' }))
    expect(localStorage.getItem(RETENTION_MODE_KEY)).toBe('archive')
    expect(await screen.findByText('Retention saved')).toBeInTheDocument()
  })

  it('persists a hostname override and toasts on save', async () => {
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'Hostname' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Hostname override' }), {
      target: { value: 'swarm.example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save hostname' }))
    expect(localStorage.getItem(HOSTNAME_OVERRIDE_KEY)).toBe('swarm.example.com')
    expect(await screen.findByText('Hostname saved')).toBeInTheDocument()
  })

  it('lists configured profiles and persists the Default picker', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = (init?.method || 'GET').toUpperCase()
      if (url.includes('/v1/llm-profiles') && method === 'PATCH') {
        const body = JSON.parse(String(init?.body || '{}'))
        return {
          ok: true,
          status: 200,
          json: async () => ({
            object: 'llm_profiles',
            profiles: [
              { id: 'gpt-5.6-terra', object: 'llm_profile', source: 'config', owned_by: 'openai' },
              { id: 'gpt-4o-mini', object: 'llm_profile', source: 'config', owned_by: 'openai' },
            ],
            default_llm_profile: body.default_llm_profile,
            default_is_auto: false,
            override_per_task: Boolean(body.override_per_task),
            task_llm_profiles: body.task_llm_profiles || {},
            auto_picks: { default: 'gpt-5.6-terra' },
            warnings: [],
            routes: {},
            task_classes: ['orchestration', 'auxiliary', 'delegation'],
          }),
        } as Response
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({
          object: 'llm_profiles',
          profiles: [
            { id: 'gpt-5.6-terra', object: 'llm_profile', source: 'config', owned_by: 'openai' },
            { id: 'gpt-4o-mini', object: 'llm_profile', source: 'config', owned_by: 'openai' },
          ],
          default_llm_profile: 'gpt-5.6-terra',
          default_is_auto: true,
          override_per_task: false,
          task_llm_profiles: {
            orchestration: 'gpt-5.6-terra',
            auxiliary: 'gpt-4o-mini',
            delegation: 'gpt-5.6-terra',
          },
          auto_picks: { default: 'gpt-5.6-terra', auxiliary: 'gpt-4o-mini' },
          warnings: [],
          routes: {},
          task_classes: ['orchestration', 'auxiliary', 'delegation'],
        }),
      } as Response
    })
    vi.stubGlobal('fetch', fetchMock)
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'LLM profiles' }))
    expect(await screen.findByRole('list', { name: 'Configured LLM profiles' })).toBeInTheDocument()
    const defaultSelect = await screen.findByLabelText('Default')
    expect(defaultSelect).toHaveValue('gpt-5.6-terra')
    fireEvent.change(defaultSelect, { target: { value: 'gpt-4o-mini' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save LLM profiles' }))
    expect(await screen.findByText('LLM profiles saved')).toBeInTheDocument()
    const patchCall = fetchMock.mock.calls.find(
      (call) => String(call[0]).includes('/v1/llm-profiles') && call[1]?.method === 'PATCH',
    )
    expect(patchCall).toBeTruthy()
    expect(JSON.parse(String(patchCall?.[1]?.body))).toMatchObject({
      default_llm_profile: 'gpt-4o-mini',
      override_per_task: false,
    })
  })

  it('hides the per-task map when override is off', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          object: 'llm_profiles',
          profiles: [
            { id: 'gpt-5.6-terra', object: 'llm_profile', source: 'config', owned_by: 'openai' },
            { id: 'o3', object: 'llm_profile', source: 'config', owned_by: 'openai' },
          ],
          default_llm_profile: 'gpt-5.6-terra',
          default_is_auto: false,
          override_per_task: false,
          task_llm_profiles: { delegation: 'o3' },
          auto_picks: { default: 'gpt-5.6-terra' },
          warnings: [],
          routes: {},
          task_classes: ['orchestration', 'auxiliary', 'delegation'],
        }),
      } as Response),
    )
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'LLM profiles' }))
    expect(await screen.findByLabelText('Default')).toBeInTheDocument()
    expect(screen.getByRole('switch', { name: 'Override per task' })).toHaveAttribute(
      'aria-checked',
      'false',
    )
    expect(screen.queryByLabelText('Delegation (design / coding)')).not.toBeInTheDocument()
  })

  it('shows the per-task map when override is on', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          object: 'llm_profiles',
          profiles: [
            { id: 'gpt-5.6-terra', object: 'llm_profile', source: 'config', owned_by: 'openai' },
            { id: 'o3', object: 'llm_profile', source: 'config', owned_by: 'openai' },
          ],
          default_llm_profile: 'gpt-5.6-terra',
          default_is_auto: false,
          override_per_task: true,
          task_llm_profiles: {
            orchestration: 'gpt-5.6-terra',
            auxiliary: 'gpt-5.6-terra',
            delegation: 'o3',
          },
          auto_picks: { default: 'gpt-5.6-terra' },
          warnings: [],
          routes: {},
          task_classes: ['orchestration', 'auxiliary', 'delegation'],
        }),
      } as Response),
    )
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'LLM profiles' }))
    expect(await screen.findByLabelText('Delegation (design / coding)')).toHaveValue('o3')
    expect(screen.getByLabelText('Auxiliary (code summary)')).toBeInTheDocument()
    expect(screen.getByRole('switch', { name: 'Override per task' })).toHaveAttribute(
      'aria-checked',
      'true',
    )
  })

  it('warns when a selected profile is missing from the catalog', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          object: 'llm_profiles',
          profiles: [
            { id: 'gpt-5.6-terra', object: 'llm_profile', source: 'config', owned_by: 'openai' },
          ],
          default_llm_profile: 'missing-slug',
          default_is_auto: false,
          override_per_task: false,
          task_llm_profiles: {},
          auto_picks: { default: 'gpt-5.6-terra' },
          warnings: ["LLM profile 'missing-slug' not found; falling back to 'gpt-5.6-terra'."],
          routes: {},
          task_classes: ['orchestration', 'auxiliary', 'delegation'],
        }),
      } as Response),
    )
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'LLM profiles' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/missing-slug/)
    expect(screen.getByRole('alert')).toHaveTextContent(/gpt-5.6-terra/)
  })

  it('calls onClose from the sheet Close button', () => {
    const { onClose } = renderSheet()
    fireEvent.click(screen.getByRole('button', { name: /^Close$/ }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('shows a System section with local store facts and no Django copy', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          path: '~/share/swarm/store.db',
          size_bytes: 13_002_342,
          size_label: '12.4 MB',
          created: true,
          conversation_count: 3,
          message_count: 11,
        }),
      } as Response),
    )
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'System' }))
    const heading = await screen.findByRole('heading', { name: 'System' })
    expect(await screen.findByText('12.4 MB')).toBeInTheDocument()
    expect(screen.getByText('~/share/swarm/store.db')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('11')).toBeInTheDocument()
    expect(screen.getByText(/local database on this machine/i)).toBeInTheDocument()
    const pane = heading.closest('section')
    const copy = pane?.textContent ?? ''
    expect(copy).not.toMatch(/Django/i)
    expect(copy).not.toMatch(/sqlite3/i)
    expect(copy).not.toMatch(/\bORM\b/i)
  })

  it('shows 0 and not created yet when the local store is missing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('offline')),
    )
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'System' }))
    expect((await screen.findAllByText('not created yet')).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Conversations').closest('div')).toHaveTextContent('0')
    expect(screen.getByText('Messages').closest('div')).toHaveTextContent('0')
    const pane = screen.getByRole('heading', { name: 'System' }).closest('section')
    expect(pane?.textContent).not.toMatch(/Django/i)
  })

  it('keeps the Django operator dump link', () => {
    renderSheet()
    expect(screen.getByRole('link', { name: 'Operator dump' })).toHaveAttribute(
      'href',
      '/settings/',
    )
  })
})

describe('SettingsSheet blueprint editor', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('opens as a DaisyUI modal-end sheet selected to Blueprint', () => {
    renderSheet({ blueprintId: 'gate' })
    const dialog = screen.getByRole('dialog', { hidden: true })
    expect(dialog).toHaveClass('modal')
    expect(dialog).toHaveClass('modal-end')
    expect(dialog).not.toHaveClass('drawer')
    expect(screen.getByRole('button', { name: 'Blueprint' })).toHaveClass('menu-active')
    expect(screen.getByRole('heading', { name: 'Blueprint' })).toBeInTheDocument()
  })

  it('shows highlighted gate YES/NO Python when source is missing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ error: 'blueprint not found' }),
      } as Response),
    )
    renderSheet({ blueprintId: 'gate' })
    const code = await screen.findByLabelText(/Gate blueprint Python/i)
    expect(code).toHaveClass('os-code-python')
    expect(code.textContent).toMatch(/YES/)
    expect(code.textContent).toMatch(/NO/)
    expect(code.querySelector('.os-py-kw')).toBeTruthy()
    expect(screen.getByTitle('src/swarm/core/tool_gate.py')).toHaveTextContent('tool_gate')
    expect(screen.queryByText(/Teams drop-zone/i)).not.toBeInTheDocument()
  })

  it('shows skeptic retry recipe', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ error: 'blueprint not found' }),
      } as Response),
    )
    renderSheet({ blueprintId: 'skeptic' })
    const code = await screen.findByLabelText(/Skeptic blueprint Python/i)
    expect(code.textContent).toMatch(/SKEPTIC_MAX_RETRIES/)
    expect(code.textContent).toMatch(/retry/)
  })

  it('renders live source when the API returns Python', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          id: 'support',
          files: [{ name: 'blueprint_support.py', path: 'blueprint_support.py' }],
          primary: 'blueprint_support.py',
          selected: 'blueprint_support.py',
          content: 'def ask_user(question):\n    return question\n',
        }),
      } as Response),
    )
    renderSheet({ blueprintId: 'support' })
    const code = await screen.findByLabelText(/Support blueprint Python/i)
    await waitFor(() => {
      expect(code.textContent).toMatch(/ask_user/)
    })
    expect(screen.getByRole('link', { name: 'blueprint_support.py' })).toHaveAttribute(
      'href',
      '/v1/blueprints/support/source?file=blueprint_support.py',
    )
  })

  it('REQ-19 #334: switches Blueprint file tabs and refetches the selected file', async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo) => {
      const url = String(input)
      const selected = url.includes('roles.py') ? 'roles.py' : 'blueprint_support.py'
      return {
        ok: true,
        status: 200,
        json: async () => ({
          id: 'support',
          files: [
            { name: 'blueprint_support.py', path: 'blueprint_support.py' },
            { name: 'roles.py', path: 'roles.py' },
          ],
          primary: 'blueprint_support.py',
          selected,
          content:
            selected === 'roles.py'
              ? 'ROLE = "support"\n'
              : 'def ask_user(question):\n    return question\n',
        }),
      } as Response
    })
    vi.stubGlobal('fetch', fetchMock)
    renderSheet({ blueprintId: 'support' })
    const tabs = await screen.findByRole('tablist', { name: 'Blueprint files' })
    expect(within(tabs).getByRole('tab', { name: 'blueprint_support.py' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    fireEvent.click(within(tabs).getByRole('tab', { name: 'roles.py' }))
    await waitFor(() => {
      expect(screen.getByLabelText(/Support blueprint Python/i).textContent).toMatch(/ROLE/)
    })
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('file=roles.py'))).toBe(
      true,
    )
  })

  it('calls onClose from the sheet Close button', () => {
    const { onClose } = renderSheet({ blueprintId: 'gate' })
    fireEvent.click(screen.getByRole('button', { name: /^Close$/ }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})

describe('SettingsSheet definition pane (REQ-42)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('opens focused on the role definition with the static explanation', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          kind: 'role',
          id: 'gate',
          title: 'Gate',
          role: 'gate',
          explanation: 'Gate is a YES/NO classifier.',
          source: 'GATE_INSTRUCTIONS',
          injected: {
            system_prompt: '',
            tools: {},
            metadata: {},
            handoff: '',
            extra: 'fixture',
          },
          default_llm: { configured: false, model: null },
        }),
      } as Response),
    )
    renderSheet({
      blueprintId: 'gate',
      initialSection: 'definition',
      definitionKind: 'role',
      definitionId: 'gate',
    })
    const dialog = screen.getByRole('dialog', { hidden: true })
    expect(dialog).toHaveClass('modal-end')
    expect(screen.getByRole('button', { name: 'Definition' })).toHaveClass('menu-active')
    const pane = await screen.findByRole('region', { name: /gate/i })
    expect(pane).toHaveAttribute('data-definition-id', 'gate')
    expect(screen.getByTestId('definition-explanation').textContent).toMatch(/YES\/NO/)
    expect(screen.queryByLabelText(/Gate blueprint Python/i)).not.toBeInTheDocument()
  })
})
