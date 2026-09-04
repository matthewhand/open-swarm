import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ToastProvider } from '../../components/DaisyUI'
import {
  COPY_EMPTY_TITLE,
  COPY_FAILED_TITLE,
} from '../../lib/clipboard'
import { ChatMessageActions } from '../ChatMessageActions'

function renderActions(text: string, onRetry?: () => void) {
  return render(
    <ToastProvider>
      <ChatMessageActions text={text} onRetry={onRetry} />
    </ToastProvider>,
  )
}

describe('ChatMessageActions', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('copies full raw text and shows Copied', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })

    renderActions('hello **markdown**')
    fireEvent.click(screen.getByRole('button', { name: 'Copy message' }))

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith('hello **markdown**')
    })
    expect(await screen.findByRole('button', { name: 'Copied' })).toBeInTheDocument()
    expect(screen.getByText('Copied')).toBeInTheDocument()
  })

  it('falls back to execCommand when the Clipboard API rejects', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) },
    })
    const exec = vi.spyOn(document, 'execCommand').mockReturnValue(true)

    renderActions('fallback body')
    fireEvent.click(screen.getByRole('button', { name: 'Copy message' }))

    await waitFor(() => {
      expect(exec).toHaveBeenCalledWith('copy')
    })
    expect(await screen.findByRole('button', { name: 'Copied' })).toBeInTheDocument()
    expect(screen.queryByText(COPY_FAILED_TITLE)).not.toBeInTheDocument()
  })

  it('toasts Copy failed when clipboard and fallback both fail', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) },
    })
    vi.spyOn(document, 'execCommand').mockReturnValue(false)

    renderActions('still stuck')
    fireEvent.click(screen.getByRole('button', { name: 'Copy message' }))

    expect(await screen.findByText(COPY_FAILED_TITLE)).toBeInTheDocument()
    expect(screen.queryByText('Copied')).not.toBeInTheDocument()
  })

  it('disables Copy when there is nothing to copy', () => {
    renderActions('   ')
    expect(screen.getByRole('button', { name: COPY_EMPTY_TITLE })).toBeDisabled()
  })

  it('wires Retry and does not mount react/reply/more stubs', () => {
    const onRetry = vi.fn()
    renderActions('hi', onRetry)
    fireEvent.click(screen.getByRole('button', { name: 'Resend the previous message' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('button', { name: /react/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /reply/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /more/i })).not.toBeInTheDocument()
  })
})
