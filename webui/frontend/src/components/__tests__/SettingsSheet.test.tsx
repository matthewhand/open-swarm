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

    const remotesToggle = screen.getByRole('button', { name: 'Remotes' })
    expect(remotesToggle).toHaveClass('menu-dropdown-toggle')
    expect(remotesToggle).toHaveClass('menu-dropdown-show')
    expect(screen.getByRole('radiogroup', { name: 'Retention mode' })).toHaveClass('join')
    expect(screen.getByRole('button', { name: 'Blueprint' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /add remote/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Hermes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'OMB' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Rakazo' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retention' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Hostname' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'LLM profiles' })).toBeInTheDocument()
  })

  it('shows remotes empty-until-add and join radios for retention', async () => {
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: /add remote/i }))
    expect(await screen.findByRole('heading', { name: 'Add remote' })).toBeInTheDocument()
    expect(screen.getByText(/no remotes configured yet/i)).toBeInTheDocument()
    expect(screen.queryByText(/placeholder remote/i)).not.toBeInTheDocument()

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

const RAKAZO_KIND = {
  id: 'rakazo',
  label: 'Rakazo',
  fields: ['base_url', 'ui_url', 'api_key_env', 'session_cookie_env'],
  ops: ['health', 'list', 'send'],
}

const RAKAZO_REMOTE = {
  id: 'rakazo',
  kind: 'rakazo',
  title: 'Rakazo',
  label: 'Rakazo',
  host_label: '',
  base_url: 'http://127.0.0.1:9',
  ui_url: 'http://127.0.0.1:9',
  api_key_env: 'RAKAZO_API_KEY',
  session_cookie_env: 'RAKAZO_SESSION_COOKIE',
  api_key_set: false,
  cookie_set: false,
  configured: true,
  notes: 'GET /health public; RPC needs auth',
  source: 'config',
}

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

describe('SettingsSheet Rakazo remote kind', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('adds rakazo with env-var names and then health/list/send', async () => {
    let configured = false
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = (init?.method || 'GET').toUpperCase()
      if (url.includes('/v1/remotes/') && method === 'GET' && !url.includes('/health') && !url.includes('/operate')) {
        return jsonResponse({
          object: 'list',
          data: configured ? [RAKAZO_REMOTE] : [],
          kinds: [RAKAZO_KIND],
        })
      }
      if (url.endsWith('/v1/remotes/') && method === 'POST') {
        const body = JSON.parse(String(init?.body || '{}'))
        expect(body.kind).toBe('rakazo')
        expect(body.api_key_env).toBe('RAKAZO_API_KEY')
        expect(body.session_cookie_env).toBe('RAKAZO_SESSION_COOKIE')
        expect(JSON.stringify(body)).not.toMatch(/sid=|token/i)
        configured = true
        return jsonResponse({ ...RAKAZO_REMOTE, persisted_to: '/tmp/swarm_config.json' })
      }
      if (url.includes('/v1/remotes/rakazo/health') && method === 'POST') {
        return jsonResponse({
          remote: 'rakazo',
          ok: true,
          state: 'UP',
          detail: 'tcp 1ms · http 200 on /health',
          http_status: 200,
        })
      }
      if (url.includes('/v1/remotes/rakazo/operate') && method === 'POST') {
        const body = JSON.parse(String(init?.body || '{}'))
        if (body.op === 'list') {
          return jsonResponse({
            remote: 'rakazo',
            op: 'list',
            ok: false,
            detail: 'Rakazo /rpc/bots/list requires a Better Auth session.',
            http_status: 401,
            gap: 'rakazo_rpc_requires_better_auth_session',
            data: { error: 'UNAUTHORIZED' },
          })
        }
        return jsonResponse({
          remote: 'rakazo',
          op: 'send',
          ok: true,
          detail: 'sent Rakazo thread via POST /rpc/threads/send (bot bot-9)',
          http_status: 200,
          data: { json: { taskId: 't1' } },
        })
      }
      return jsonResponse({ object: 'list', data: [] })
    })
    vi.stubGlobal('fetch', fetchMock)

    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: /add remote/i }))
    expect(await screen.findByRole('heading', { name: 'Add remote' })).toBeInTheDocument()
    expect(screen.queryByLabelText(/api key$/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/^cookie$/i)).not.toBeInTheDocument()

    fireEvent.change(screen.getByRole('textbox', { name: 'API base URL' }), {
      target: { value: 'http://127.0.0.1:9' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'UI URL (optional)' }), {
      target: { value: 'http://127.0.0.1:9' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'API key env' }), {
      target: { value: 'RAKAZO_API_KEY' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Session cookie env' }), {
      target: { value: 'RAKAZO_SESSION_COOKIE' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save remote' }))

    expect(await screen.findByRole('heading', { name: 'Rakazo' })).toBeInTheDocument()
    expect(screen.getByText('RAKAZO_API_KEY')).toBeInTheDocument()
    expect(screen.getByText('RAKAZO_SESSION_COOKIE')).toBeInTheDocument()
    expect(screen.queryByText(/sid=/i)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Check health' }))
    expect(await screen.findByText(/Health UP/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'List bots' }))
    expect(await screen.findByText(/Better Auth/i)).toBeInTheDocument()
    expect(screen.getByText('rakazo_rpc_requires_better_auth_session')).toBeInTheDocument()

    fireEvent.change(screen.getByRole('textbox', { name: 'Bot id' }), {
      target: { value: 'bot-9' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Message' }), {
      target: { value: 'go' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^Send$/ }))
    expect(await screen.findByText(/sent Rakazo thread/i)).toBeInTheDocument()
  })

  it('refuses pasted cookies on the add form', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/v1/remotes/')) {
          return jsonResponse({ object: 'list', data: [], kinds: [RAKAZO_KIND] })
        }
        return jsonResponse({ object: 'list', data: [] })
      }),
    )
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: /add remote/i }))
    fireEvent.change(await screen.findByRole('textbox', { name: 'API base URL' }), {
      target: { value: 'http://127.0.0.1:9' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Session cookie env' }), {
      target: { value: 'sid=super-secret' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save remote' }))
    expect(await screen.findByText(/env-var names only/i)).toBeInTheDocument()
  })
})
