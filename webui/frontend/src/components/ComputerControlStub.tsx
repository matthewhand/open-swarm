import { useEffect, useId, useRef, useState } from 'react'
import { Monitor } from 'lucide-react'

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
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open) {
      if (!dialog.open) dialog.showModal()
    } else if (dialog.open) {
      dialog.close()
    }
  }, [open])

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    const onCancel = (event: Event) => {
      event.preventDefault()
      setOpen(false)
    }
    const onNativeClose = () => setOpen(false)
    dialog.addEventListener('cancel', onCancel)
    dialog.addEventListener('close', onNativeClose)
    return () => {
      dialog.removeEventListener('cancel', onCancel)
      dialog.removeEventListener('close', onNativeClose)
    }
  }, [])

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
      <dialog
        ref={dialogRef}
        className={`modal ${open ? 'modal-open' : ''}`}
        aria-labelledby={titleId}
        aria-modal={open ? true : undefined}
      >
        <div className="modal-box max-w-sm">
          <h3 id={titleId} className="font-bold text-lg">
            Computer control
          </h3>
          <div className="mt-3 space-y-3">
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
        </div>
        <form method="dialog" className="modal-backdrop" onSubmit={close}>
          <button type="submit" aria-label="Close modal">
            close
          </button>
        </form>
      </dialog>
    </>
  )
}

export default ComputerControlStub
