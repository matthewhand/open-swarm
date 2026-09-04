import { useEffect } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ToastProvider, TOAST_KIND_WS_DISCONNECT, useToast } from '../Toast'

function ToastProbe() {
  const { addToast, dismissByKind } = useToast()
  return (
    <div>
      <button
        type="button"
        onClick={() =>
          addToast({
            kind: TOAST_KIND_WS_DISCONNECT,
            type: 'error',
            title: 'Chat disconnected',
            message: 'The chat websocket closed.',
          })
        }
      >
        fire-disconnect
      </button>
      <button
        type="button"
        onClick={() =>
          addToast({
            kind: TOAST_KIND_WS_DISCONNECT,
            type: 'error',
            title: 'Chat websocket unreachable',
            message: 'ASGI is not serving /ws/.',
          })
        }
      >
        fire-unreachable
      </button>
      <button
        type="button"
        onClick={() =>
          addToast({
            type: 'info',
            title: 'Copied',
            message: 'Message copied.',
          })
        }
      >
        fire-copy
      </button>
      <button type="button" onClick={() => dismissByKind(TOAST_KIND_WS_DISCONNECT)}>
        dismiss-disconnect
      </button>
    </div>
  )
}

function disconnectToasts() {
  return document.querySelectorAll(`[data-toast-kind="${TOAST_KIND_WS_DISCONNECT}"]`)
}

describe('Toast kind dedupe (REQ-112 #489)', () => {
  it('keeps at most one disconnect toast and updates it instead of stacking', () => {
    render(
      <ToastProvider>
        <ToastProbe />
      </ToastProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'fire-disconnect' }))
    fireEvent.click(screen.getByRole('button', { name: 'fire-disconnect' }))
    fireEvent.click(screen.getByRole('button', { name: 'fire-unreachable' }))

    expect(disconnectToasts()).toHaveLength(1)
    expect(screen.getByText('Chat websocket unreachable')).toBeInTheDocument()
    expect(screen.queryByText('Chat disconnected')).not.toBeInTheDocument()
  })

  it('dismisses only disconnect-kind toasts, leaving unrelated ones', () => {
    render(
      <ToastProvider>
        <ToastProbe />
      </ToastProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'fire-disconnect' }))
    fireEvent.click(screen.getByRole('button', { name: 'fire-copy' }))
    expect(screen.getByText('Chat disconnected')).toBeInTheDocument()
    expect(screen.getByText('Copied')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'dismiss-disconnect' }))

    expect(disconnectToasts()).toHaveLength(0)
    expect(screen.queryByText('Chat disconnected')).not.toBeInTheDocument()
    expect(screen.getByText('Copied')).toBeInTheDocument()
    expect(screen.getByText('Message copied.')).toBeInTheDocument()
  })

  it('does not stack when a consumer remounts and fires the same kind again', () => {
    function FireOnMount() {
      const { addToast } = useToast()
      useEffect(() => {
        addToast({
          kind: TOAST_KIND_WS_DISCONNECT,
          type: 'error',
          title: 'Chat disconnected',
          message: 'The chat websocket closed.',
        })
      }, [addToast])
      return null
    }

    const { rerender } = render(
      <ToastProvider>
        <FireOnMount key="first" />
      </ToastProvider>,
    )
    expect(disconnectToasts()).toHaveLength(1)

    rerender(
      <ToastProvider>
        <FireOnMount key="second" />
      </ToastProvider>,
    )
    expect(disconnectToasts()).toHaveLength(1)
    expect(screen.getAllByText('Chat disconnected')).toHaveLength(1)
  })
})
