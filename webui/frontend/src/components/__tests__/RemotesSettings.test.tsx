import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RemoteOperatePane } from '../RemotesSettings'
import { ToastProvider } from '../DaisyUI'
import * as api from '../../lib/api'

function renderPane(remote = { id: 'omb', label: 'OpenMousBot', base_url: 'http://localhost:8000' }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <RemoteOperatePane remote={remote as any} />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

describe('RemotesSettings RemoteOperatePane (REQ-131)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders List bots button and stops spinner on success', async () => {
    vi.spyOn(api, 'operateRemote').mockResolvedValue({
      remote: 'omb',
      op: 'list',
      ok: true,
      detail: 'OpenMousBot listed 2 bot(s) via GET /api/bots',
      data: { bots: [{ id: 'bot-1', name: 'Alpha Bot' }, { id: 'bot-2', name: 'Beta Bot' }] },
    })

    renderPane()

    const listBtn = screen.getByRole('button', { name: /list bots/i })
    expect(listBtn).toBeInTheDocument()

    fireEvent.click(listBtn)

    await waitFor(() => {
      expect(screen.getByText(/bot-1 · Alpha Bot/i)).toBeInTheDocument()
      expect(screen.getByText(/bot-2 · Beta Bot/i)).toBeInTheDocument()
      expect(listBtn).not.toHaveAttribute('aria-busy', 'true')
    })
  })

  it('stops spinner and renders error alert when list times out or fails', async () => {
    vi.spyOn(api, 'operateRemote').mockRejectedValue(
      new Error('OpenMousBot list operation timed out after 12s. Remote server is slow or hung.'),
    )

    renderPane()

    const listBtn = screen.getByRole('button', { name: /list bots/i })
    fireEvent.click(listBtn)

    await waitFor(() => {
      expect(
        screen.getByText(/OpenMousBot list operation timed out after 12s/i),
      ).toBeInTheDocument()
      expect(listBtn).not.toHaveAttribute('aria-busy', 'true')
    })
  })
})
