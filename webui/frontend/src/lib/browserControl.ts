/**
 * REQ-45 browser-control targets. Playwright-on-this-machine is the default.
 * Sandbox/SaaS rows are clickable WIP — not wired, never selected as working.
 */

export const BROWSER_THIS_MACHINE = 'this_machine'
export const BROWSER_SANDBOX = 'sandbox'
export const BROWSER_SAAS = 'saas'

export type BrowserTargetId = typeof BROWSER_THIS_MACHINE | typeof BROWSER_SANDBOX | typeof BROWSER_SAAS

export interface BrowserTarget {
  id: BrowserTargetId
  label: string
  wired: boolean
  todo: boolean
  detail: string
}

export const BROWSER_TARGETS: BrowserTarget[] = [
  {
    id: BROWSER_THIS_MACHINE,
    label: 'Browser (this machine)',
    wired: true,
    todo: false,
    detail: 'Playwright launches or attaches local Chrome on the machine that runs the agent.',
  },
  {
    id: BROWSER_SANDBOX,
    label: 'Sandbox / Docker',
    wired: false,
    todo: true,
    detail: 'OMB/Rakazo-style sandboxed browser. Future — not wired.',
  },
  {
    id: BROWSER_SAAS,
    label: 'SaaS',
    wired: false,
    todo: true,
    detail: 'Hosted browser. Future — not wired. No live paid checkout.',
  },
]

export const DEFAULT_BROWSER_TARGET: BrowserTargetId = BROWSER_THIS_MACHINE

export function wipCopyForTarget(id: BrowserTargetId): string {
  if (id === BROWSER_SANDBOX) {
    return 'Sandbox / Docker browser provider is TODO — not wired.'
  }
  if (id === BROWSER_SAAS) {
    return 'SaaS browser provider is TODO — not wired.'
  }
  return ''
}

export interface BrowserControlCatalog {
  default: BrowserTargetId
  targets: BrowserTarget[]
  driver?: string
  desktop_os?: string
}

export function parseBrowserCatalog(raw: unknown): BrowserControlCatalog {
  const fallback: BrowserControlCatalog = {
    default: DEFAULT_BROWSER_TARGET,
    targets: BROWSER_TARGETS,
    driver: 'playwright',
    desktop_os: 'out_of_scope',
  }
  if (!raw || typeof raw !== 'object') return fallback
  const body = raw as Record<string, unknown>
  if (body.default !== BROWSER_THIS_MACHINE) return fallback
  return {
    default: BROWSER_THIS_MACHINE,
    targets: BROWSER_TARGETS,
    driver: typeof body.driver === 'string' ? body.driver : 'playwright',
    desktop_os: typeof body.desktop_os === 'string' ? body.desktop_os : 'out_of_scope',
  }
}
