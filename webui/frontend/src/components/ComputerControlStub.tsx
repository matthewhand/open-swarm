import { useEffect, useState } from 'react'
import { Monitor } from 'lucide-react'
import { Modal } from './DaisyUI'
import ComputerRoutinesPane from './ComputerRoutinesPane'
import { notifyOverlayClosed, OPEN_COMPUTER_CONTROL_EVENT } from '../lib/chromeOverlay'

/**
 * REQ-80 / #432 — computer-icon right pane: screen thumbnail + Routines.
 *
 * Replaces the REQ-27b placeholder dialog. Click expands a DaisyUI modal-end
 * pane over mounted Chat (REQ-48 / #364). No driver, no live host thumbnail,
 * no secrets.
 */
export interface ComputerControlStubProps {
  agentId?: string
  agentName?: string
  hasScreenSession?: boolean
}

export function ComputerControlStub({
  agentId = '',
  agentName = 'Agent',
  hasScreenSession = false,
}: ComputerControlStubProps) {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const onOpen = () => setOpen(true)
    window.addEventListener(OPEN_COMPUTER_CONTROL_EVENT, onOpen)
    return () => window.removeEventListener(OPEN_COMPUTER_CONTROL_EVENT, onOpen)
  }, [])

  const close = () => {
    setOpen(false)
    notifyOverlayClosed()
  }

  return (
    <>
      <div className="tooltip tooltip-bottom" data-tip="Computer control">
        <button
          type="button"
          className="btn btn-ghost btn-sm btn-square"
          aria-label="Computer control"
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => setOpen(true)}
        >
          <Monitor className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      <Modal
        isOpen={open}
        onClose={close}
        placement="end"
        size="sheet"
        className="flex min-h-0 max-w-sm flex-col"
        aria-label="Computer control"
      >
        <ComputerRoutinesPane
          agentId={agentId}
          agentName={agentName}
          hasScreenSession={hasScreenSession}
        />
      </Modal>
    </>
  )
}

export default ComputerControlStub
