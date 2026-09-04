/**
 * Computer / browser control pane (REQ-48 host for #341 / #361).
 *
 * Browser-on-this-machine is the chosen default. Sandbox / Docker and SaaS
 * rows are visible, greyed TODO — not wired and not pretended to work.
 */

export type ComputerControlMode = 'browser-local' | 'sandbox-docker' | 'saas'

const MODES: {
  id: ComputerControlMode
  label: string
  hint: string
  enabled: boolean
}[] = [
  {
    id: 'browser-local',
    label: 'Browser (this machine)',
    hint: 'Default. Playwright drives Chrome on this host.',
    enabled: true,
  },
  {
    id: 'sandbox-docker',
    label: 'Sandbox / Docker',
    hint: 'TODO — isolated browser later. Not wired.',
    enabled: false,
  },
  {
    id: 'saas',
    label: 'SaaS',
    hint: 'TODO — remote hosted browser later. Not wired.',
    enabled: false,
  },
]

export default function ComputerControlPane() {
  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-lg font-semibold">Computer control</h4>
        <p className="mt-1 text-sm text-base-content/70">
          Agents drive a bare-metal browser on this machine. Desktop OS
          automation is out of scope.
        </p>
      </div>
      <fieldset>
        <legend className="sr-only">Computer control mode</legend>
        <ul className="space-y-2">
          {MODES.map((mode) => (
            <li key={mode.id}>
              <label
                className={`flex cursor-pointer items-start gap-3 rounded-lg border border-base-300 px-3 py-2 ${
                  mode.enabled ? 'bg-base-200/60' : 'cursor-not-allowed opacity-45'
                }`}
              >
                <input
                  type="radio"
                  name="computer-control-mode"
                  value={mode.id}
                  defaultChecked={mode.id === 'browser-local'}
                  disabled={!mode.enabled}
                  aria-label={mode.label}
                  className="radio radio-sm mt-1"
                />
                <span>
                  <span className="block text-sm font-medium">{mode.label}</span>
                  <span className="block text-xs text-base-content/60">{mode.hint}</span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      </fieldset>
    </div>
  )
}
