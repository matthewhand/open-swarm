import { useMemo, useState } from 'react'
import { Globe } from 'lucide-react'
import { Alert, Badge, Modal } from './DaisyUI'
import {
  BROWSER_TARGETS,
  BROWSER_THIS_MACHINE,
  DEFAULT_BROWSER_TARGET,
  wipCopyForTarget,
  type BrowserTargetId,
} from '../lib/browserControl'

/**
 * REQ-45 browser-control pane. Playwright-on-this-machine is selected.
 * Sandbox / SaaS rows are greyed, clickable WIP, and never become the live target.
 */
export default function BrowserControlPane() {
  const [open, setOpen] = useState(false)
  const [wip, setWip] = useState<string | null>(null)
  const selected = DEFAULT_BROWSER_TARGET

  const rows = useMemo(() => BROWSER_TARGETS, [])

  const handleRow = (id: BrowserTargetId) => {
    if (id === BROWSER_THIS_MACHINE) {
      setWip(null)
      return
    }
    setWip(wipCopyForTarget(id))
  }

  return (
    <>
      <button
        type="button"
        className="btn btn-ghost btn-sm btn-square"
        aria-label="Browser control"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen(true)}
      >
        <Globe className="h-4 w-4" aria-hidden="true" />
      </button>
      <Modal
        isOpen={open}
        onClose={() => {
          setOpen(false)
          setWip(null)
        }}
        title="Browser control"
        size="md"
      >
        <p className="mb-3 text-sm text-base-content/70">
          Agents use the same Playwright tool from CLI, API, or a remote seat.
          Default is this machine. Sandbox/SaaS providers are listed so they
          are not pretended to work. Desktop/OS control stays on the #341 stub.
        </p>
        <ul className="os-browser-targets" aria-label="Browser providers">
          {rows.map((row) => {
            const isSelected = row.id === selected && !row.todo
            return (
              <li key={row.id}>
                <button
                  type="button"
                  className={`os-browser-target ${row.todo ? 'os-browser-target--todo' : ''} ${
                    isSelected ? 'os-browser-target--selected' : ''
                  }`}
                  aria-pressed={isSelected}
                  data-target={row.id}
                  data-todo={row.todo ? 'true' : 'false'}
                  onClick={() => handleRow(row.id)}
                >
                  <span className="os-browser-target__radio" aria-hidden="true" />
                  <span className="min-w-0 flex-1 text-left">
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{row.label}</span>
                      {row.todo ? (
                        <Badge type="ghost" size="sm">
                          TODO
                        </Badge>
                      ) : (
                        <Badge type="success" size="sm" outline>
                          Default
                        </Badge>
                      )}
                    </span>
                    <span className="mt-0.5 block text-xs text-base-content/65">{row.detail}</span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
        {wip ? (
          <Alert type="warning" className="mt-3" role="status">
            {wip} Browser (this machine) stays selected.
          </Alert>
        ) : (
          <p className="mt-3 text-xs text-base-content/55">
            Missing Chrome returns an error; the app does not crash. No live preview.
          </p>
        )}
      </Modal>
    </>
  )
}
