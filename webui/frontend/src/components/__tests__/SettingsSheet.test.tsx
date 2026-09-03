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
    expect(screen.getByRole('button', { name: 'Hermes' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'OMB' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Rakazo' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retention' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Hostname' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'LLM profiles' })).toBeInTheDocument()
  })

  it('shows remotes placeholders and join radios for retention', () => {
    renderSheet()
    fireEvent.click(screen.getByRole('button', { name: 'Hermes' }))
    expect(screen.getByText(/placeholder remote/i)).toBeInTheDocument()
    expect(screen.getByText(/remotes API has not landed/i)).toBeInTheDocument()

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
