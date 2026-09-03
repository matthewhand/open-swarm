import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import SettingsSheet from '../SettingsSheet'
import { ToastProvider } from '../DaisyUI'
import {
  HOSTNAME_OVERRIDE_KEY,
  RETENTION_MODE_KEY,
} from '../../lib/settingsPrefs'

function emptyRemotesPayload() {
  return {
    object: 'list',
    kinds: [
      { id: 'hermes', label: 'Hermes' },
      { id: 'omb', label: 'OpenMousBot' },
      { id: 'rakazo', label: 'Rakazo' },
    ],
    data: [],
  }
}

function stubFetch(handler?: (url: string, init?: RequestInit) => unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (handler) {
        const custom = handler(url, init)
        if (custom !== undefined) {
          return {
            ok: true,
            status: 200,
            json: async () => custom,
          } as Response
        }
      }
      if (url.includes('/v1/remotes')) {
        return {
          ok: true,
          status: 200,
          json: async () => emptyRemotesPayload(),
        } as Response
      }
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
      return {
        ok: false,
        status: 404,
        json: async () => ({ error: 'not found' }),
      } as Response
    }),
  )
}

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
  beforeEach(() => {
    stubFetch()
  })

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
    expect(screen.getByRole('button', { name: 'Add remote' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Hermes' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'OMB' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Rakazo' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retention' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Hostname' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'LLM profiles' })).toBeInTheDocument()
  })

  it('shows empty remotes plus Add remote, and join radios for retention', async () => {
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'Remotes' }))
    expect(await screen.findByText(/No remotes configured/i)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Add remote' }).length).toBeGreaterThan(0)
    expect(screen.queryByText(/placeholder remote/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/\bOMB\b/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Retention' }))
    const group = screen.getByRole('radiogroup', { name: 'Retention mode' })
    expect(group).toHaveClass('join')
    expect(screen.getByRole('radio', { name: 'Count' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Disk' })).toHaveClass('join-item')
    expect(screen.getByRole('radio', { name: 'Archive' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Trash' })).toBeInTheDocument()
  })

  it('adds OpenMousBot and then health / list bots / send', async () => {
    let configured: Array<Record<string, unknown>> = []
    stubFetch((url, init) => {
      const method = (init?.method || 'GET').toUpperCase()
      if (url.includes('/v1/remotes/') && url.includes('/health') && method === 'POST') {
        return {
          remote: 'omb',
          ok: false,
          state: 'DOWN',
          detail: 'tcp 127.0.0.1:9 refused/timed out',
        }
      }
      if (url.includes('/v1/remotes/') && url.includes('/operate') && method === 'POST') {
        const body = JSON.parse(String(init?.body || '{}')) as { op?: string }
        if (body.op === 'send') {
          return {
            remote: 'omb',
            op: 'send',
            ok: true,
            detail: 'started OpenMousBot turn via POST /api/bots/bot-1/messages',
          }
        }
        return {
          remote: 'omb',
          op: 'list',
          ok: true,
          detail: 'OpenMousBot listed 1 bot(s) via GET /api/bots',
          data: { bots: [{ id: 'bot-1' }] },
        }
      }
      if (url.endsWith('/v1/remotes/') && method === 'POST') {
        configured = [
          {
            id: 'omb',
            label: 'OpenMousBot',
            title: 'OpenMousBot',
            base_url: 'http://127.0.0.1:9',
          },
        ]
        return configured[0]
      }
      if (url.includes('/v1/remotes') && method === 'GET') {
        return { ...emptyRemotesPayload(), data: configured }
      }
      return undefined
    })
    renderSheet()
    fireEvent.click(screen.getAllByRole('button', { name: 'Add remote' })[0])
    expect(await screen.findByRole('combobox', { name: 'Kind' })).toBeInTheDocument()
    const kind = screen.getByRole('combobox', { name: 'Kind' })
    expect(kind).toHaveTextContent('OpenMousBot')
    expect(kind).not.toHaveTextContent('OMB')
    fireEvent.change(kind, { target: { value: 'omb' } })
    fireEvent.change(screen.getByRole('textbox', { name: 'Base URL' }), {
      target: { value: 'http://127.0.0.1:9' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'API key env (optional)' }), {
      target: { value: 'OMB_API_KEY' },
    })
    const submit = screen.getAllByRole('button', { name: /^Add remote$/ }).find(
      (button) => button.getAttribute('type') === 'submit',
    )
    expect(submit).toBeTruthy()
    fireEvent.click(submit!)
    expect(await screen.findByRole('button', { name: 'OpenMousBot' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'OMB' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Health' }))
    expect(await screen.findByText('DOWN')).toBeInTheDocument()
    expect(screen.getByText(/not a crash/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'List bots' }))
    expect(await screen.findByText('bot-1')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox', { name: 'Bot id' }), {
      target: { value: 'bot-1' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Message' }), {
      target: { value: 'hello' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^Send$/ }))
    expect(await screen.findByText(/started OpenMousBot turn/i)).toBeInTheDocument()
    expect(screen.queryByText(/\bOMB\b/)).not.toBeInTheDocument()
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
