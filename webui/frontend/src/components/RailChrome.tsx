import { createContext, useContext } from 'react'
import { X } from 'lucide-react'

export const SWIPE_HINT_TEXT = 'Swipe from the left for the list'

export interface RailChromeValue {
  narrow: boolean
  railOpen: boolean
  openRail: () => void
  closeRail: () => void
}

const RailChromeContext = createContext<RailChromeValue>({
  narrow: false,
  railOpen: true,
  openRail: () => undefined,
  closeRail: () => undefined,
})

export const RailChromeProvider = RailChromeContext.Provider

export function useRailChrome(): RailChromeValue {
  return useContext(RailChromeContext)
}

export function SwipeHint({
  open,
  onDismiss,
}: {
  open: boolean
  onDismiss: () => void
}) {
  if (!open) return null
  return (
    <div role="status" className="os-swipe-hint" data-testid="os-swipe-hint">
      <p className="os-swipe-hint__text">{SWIPE_HINT_TEXT}</p>
      <button
        type="button"
        className="btn btn-ghost btn-xs btn-circle shrink-0"
        aria-label="Dismiss swipe hint"
        onClick={onDismiss}
      >
        <X className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </div>
  )
}
