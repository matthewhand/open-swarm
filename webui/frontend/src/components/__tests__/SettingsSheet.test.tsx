import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import SettingsSheet from '../SettingsSheet'
import { ToastProvider } from '../DaisyUI'
import {
  HOSTNAME_OVERRIDE_KEY,
  RETENTION_MODE_KEY,
} from '../../lib/settingsPrefs'

function renderSheet({
  isOpen = true,
  blueprintId,
}: {
  isOpen?: boolean
  blueprintId?: string
} = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const onClose = vi.fn()
  const view = render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <SettingsSheet isOpen={isOpen} onClose={onClose} blueprintId={blueprintId} />
      </ToastProvider>
    </QueryClientProvider>,
  )
  return { ...view, onClose, client }
}

describe('SettingsSheet', () => {
  afterEach(() => {
    localStorage.removeItem(HOSTNAME_OVERRIDE_KEY)
    localStorage.removeItem(RETENTION_MODE_KEY)
    vi.unstubAllGlobals()
  })

  it('opens as a DaisyUI modal-end dialog with menu sections', () => {
    renderSheet()
    const dialog = screen.getByRole('dialog', { hidden: true })
    expect(dialog).toHaveClass('modal')
    expect(dialog).toHaveClass('modal-end')
    expect(dialog).not.toHaveClass('drawer')
    expect(dialog.className).not.toMatch(/btn-group/)

    expect(screen.getByRole('button', { name: 'Remotes' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Hermes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'OMB' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Rakazo' })).not.toBeInTheDocument()
    expect(screen.getByRole('radiogroup', { name: 'Retention mode' })).toHaveClass('join')
    expect(screen.getByRole('button', { name: 'Blueprint' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retention' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Hostname' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'LLM profiles' })).toBeInTheDocument()
  })

  it('shows remotes empty state plus Add remote, not a default Hermes card', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          object: 'list',
          data: [],
          kinds: [
            {
              id: 'hermes',
              title: 'Hermes',
              label: 'Hermes',
              complete: true,
              fields: ['base_url', 'api_key_env'],
              list_paths: ['/v1/models', '/api/sessions', '/api/jobs'],
              send_path: '/v1/runs',
              health_path: '/health',
              api_key_env_default: 'HERMES_API_KEY',
            },
          ],
          team_members: [],
        }),
      } as Response),
    )
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'Remotes' }))
    expect(await screen.findByText(/No remotes added/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Add remote/i })).toBeInTheDocument()
    expect(screen.queryByText(/placeholder remote/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/OMB/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Retention' }))
    const group = screen.getByRole('radiogroup', { name: 'Retention mode' })
    expect(group).toHaveClass('join')
    expect(screen.getByRole('radio', { name: 'Count' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Disk' })).toHaveClass('join-item')
    expect(screen.getByRole('radio', { name: 'Archive' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Trash' })).toBeInTheDocument()
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

  it('after adding Hermes shows health, list, and send', async () => {
    const emptyList = {
      object: 'list',
      data: [],
      kinds: [
        {
          id: 'hermes',
          title: 'Hermes',
          label: 'Hermes',
          complete: true,
          fields: ['base_url', 'api_key_env'],
          list_paths: ['/v1/models', '/api/sessions', '/api/jobs'],
          send_path: '/v1/runs',
          health_path: '/health',
          api_key_env_default: 'HERMES_API_KEY',
        },
      ],
      team_members: [],
    }
    const added = {
      id: 'hermes',
      kind: 'hermes',
      title: 'Hermes Agent (ubuntu-gtx)',
      host_label: 'ubuntu-gtx',
      base_url: 'http://127.0.0.1:9',
      ui_url: '',
      api_key_env: 'HERMES_API_KEY',
      api_key_set: false,
      cookie_set: false,
      health_path: '/health',
      version_path: '/v1/models',
      notes: '',
      source: 'config',
      added: true,
    }
    const fetchMock = vi.fn(async (input: RequestInfo, init?: RequestInit) => {
      const url = String(input)
      const method = (init?.method || 'GET').toUpperCase()
      if (url.includes('/v1/remotes/') && method === 'GET' && !url.includes('/health') && !url.includes('/operate')) {
        const listed = fetchMock.mock.calls.some((call) => String(call[0]).endsWith('/v1/remotes/') && (call[1]?.method || 'GET').toUpperCase() === 'POST')
        return {
          ok: true,
          status: 200,
          json: async () => (listed ? { ...emptyList, data: [added] } : emptyList),
        } as Response
      }
      if (url.endsWith('/v1/remotes/') && method === 'POST') {
        return { ok: true, status: 200, json: async () => added } as Response
      }
      if (url.includes('/health/') && method === 'POST') {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            remote: 'hermes',
            ok: false,
            state: 'DOWN',
            detail: 'tcp 127.0.0.1:9 refused/timed out',
            http_status: null,
            version: null,
            latency_ms: 3,
            url: 'http://127.0.0.1:9/health',
          }),
        } as Response
      }
      if (url.includes('/operate/') && method === 'POST') {
        const body = JSON.parse(String(init?.body || '{}')) as { op?: string }
        if (body.op === 'send') {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              remote: 'hermes',
              op: 'send',
              ok: true,
              detail: 'started Hermes run via POST /v1/runs',
              http_status: 200,
              data: { run_id: 'run_1' },
              gap: '',
            }),
          } as Response
        }
        return {
          ok: true,
          status: 200,
          json: async () => ({
            remote: 'hermes',
            op: 'list',
            ok: true,
            detail: 'listed Hermes models/sessions/jobs (missing slices stay null)',
            http_status: 200,
            data: { models: { data: [{ id: 'hermes-agent' }] }, sessions: { sessions: [] }, jobs: [] },
            gap: '',
          }),
        } as Response
      }
      return { ok: true, status: 200, json: async () => ({}) } as Response
    })
    vi.stubGlobal('fetch', fetchMock)

    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'Remotes' }))
    expect(await screen.findByText(/No remotes added/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Add remote/i }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Base URL' }), {
      target: { value: 'http://127.0.0.1:9' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'API key env name' }), {
      target: { value: 'HERMES_API_KEY' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^Add$/ }))
    expect(await screen.findByText('http://127.0.0.1:9')).toBeInTheDocument()
    expect(screen.getByText(/API key env:/i)).toHaveTextContent('HERMES_API_KEY')
    expect(screen.getByRole('button', { name: 'Health' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'List' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Health' }))
    expect(await screen.findByText(/DOWN:/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'List' }))
    expect(await screen.findByText(/listed Hermes models\/sessions\/jobs/i)).toBeInTheDocument()

    fireEvent.change(screen.getByRole('textbox', { name: 'Send prompt' }), {
      target: { value: 'status' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByText(/started Hermes run via POST \/v1\/runs/i)).toBeInTheDocument()
    expect(screen.getByText(/run_1/)).toBeInTheDocument()
  })

  it('lists LLM models from the existing API when present', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          object: 'list',
          data: [{ id: 'default', object: 'model', created: 0, owned_by: 'swarm' }],
        }),
      } as Response),
    )
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'LLM profiles' }))
    expect(await screen.findByText('default')).toBeInTheDocument()
  })

  it('calls onClose from the sheet Close button', () => {
    const { onClose } = renderSheet()
    fireEvent.click(screen.getByRole('button', { name: /^Close$/ }))
    expect(onClose).toHaveBeenCalledTimes(1)
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

  it('calls onClose from the sheet Close button', () => {
    const { onClose } = renderSheet({ blueprintId: 'gate' })
    fireEvent.click(screen.getByRole('button', { name: /^Close$/ }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
