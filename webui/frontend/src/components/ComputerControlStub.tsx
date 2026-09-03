import { useState } from 'react'
import { Monitor } from 'lucide-react'
import { Modal } from './DaisyUI'

/**
 * REQ-27b Computer-control UI stub ONLY. Click says WIP. No driver, no E2B,
 * no CUA, no xdotool, no CDP.
 *
 * Intent: Show what browser/computer control will look like in open-swarm
 * chrome. Real control comes later via OMB/Rakazo remotes.
 *
 * Success:
 * 1. Chat header top-right icon tools: computer/monitor icon labeled
 *    Computer control.
 * 2. Click opens a DaisyUI modal or small pane whose body is clearly WIP
 *    (short copy: computer control will use a placed OMB or Rakazo remote;
 *    not implemented here).
 * 3. Default: icon visible, feature not attached to any agent tools. No
 *    enable-that-drives-a-machine in this PR.
 * 4. Disabled-looking is OK; do not provision sandboxes.
 *
 * Constraints: React 18 + DaisyUI 5. No Neon. No guest auth.
 */
export const COMPUTER_CONTROL_WIP_COPY =
  'Computer control will use a placed OMB or Rakazo remote; not implemented here.'

export function ComputerControlStub() {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)

  return (
    <>
      <div className="tooltip tooltip-bottom" data-tip="Computer control">
        <button
          type="button"
          className="btn btn-ghost btn-sm gap-1.5 opacity-50"
          aria-label="Computer control"
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => setOpen(true)}
        >
          <Monitor className="h-5 w-5" aria-hidden="true" />
          <span className="hidden sm:inline text-xs font-normal normal-case">
            Computer control
          </span>
        </button>
      </div>
      <Modal
        isOpen={open}
        onClose={close}
        title="Computer control"
        size="sm"
      >
        <div className="space-y-3">
          <p className="text-lg font-bold tracking-wide">WIP</p>
          <p className="text-sm text-base-content/80">
            {COMPUTER_CONTROL_WIP_COPY}
          </p>
        </div>
        <div className="modal-action">
          <button type="button" className="btn btn-sm" onClick={close}>
            Close
          </button>
        </div>
      </Modal>
    </>
  )
}

export default ComputerControlStub
